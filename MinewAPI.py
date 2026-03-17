import requests 
import json
import auth
import hashlib
from card_deck import load_template_mapping

class MinewAPI:
    def __init__(self):
        self.client = None
        self.gateway_mac = "AC233FC12EE8"
        self.STORE_ID = '1649302965594361856'
        self.DATA_ID = 'Alpha1A'
        self.BLANK_TEMPLATE_ID = '1843767205490069504'
        #self.BLANK_TEMPLATE_ID = '2022404920786817024'
        self.token = auth.get_token()
        self.tokenHeader = {'token': str(self.token)}
        self.contentTypeAndTokenHeader = {'Content-Type':'application/json;charset=utf-8', 'token': str(self.token)}
        
    ######              ######
    # GET METHODS INCLUDED
    #   connect(self), return client instance
    #   fetch_gateway_mac(self), return gateway mac address
    #   get_template_list(), return list of templates associated with store
    ######              ######
    def connect(self):
        self.client = "connected-client-object"
        # Load JSON file that stores the templateId that's being displayed on each card
        # If the file doesn't exist, create an empty dictionary
        try: 
            with open('mac_template_dict.json', 'r') as file:
                self.macTemplateDict = json.load(file)
        except FileNotFoundError:
            print("mac_template_dict.json not found, creating new dictionary")
            self.macTemplateDict = {}
        self.get_template_list()
        load_template_mapping(self)
        return True

    def fetch_gateway_mac(self):
        return self.gateway_mac

    # Returns a list of tuples containing the demoId and demoName of all templates that start with the given gameNamePrefix
    def get_template_list(self, gameNamePrefix="52"):
        templateData=requests.get(f"https://cloud.minewtag.com/apis/esl/template/findAll?page=1&size=250&storeId={self.STORE_ID}", headers=self.tokenHeader)
        #print(templateData.json())
        return [
            (template['demoId'], template['demoName']) 
            for template in templateData.json()['data']['rows'] 
            if template['demoName'].startswith(gameNamePrefix) 
                and "3.5" in template['demoName']]

    def save_and_close(self):
        # Save the macTemplateDict to the JSON file
        with open('mac_template_dict.json', 'w') as file:
            json.dump(self.macTemplateDict, file, indent=4)


    ######              ######
    # HELPER GET METHODS 
    #   getAllMacAddresses(), returns all mac addresses online
    #   used in bulk updates
    ######              ######
    # Filters out cards with a screen size of 29, which I assume are the 2.9 inch cards?
    def getAllMacAddresses(self):
        # This GET request has a maximum size of 60 that can be changed
        # I think eqstatus=2 means the card is online, and type=1 refers to the firmware type
        allTagData=requests.get(f"https://cloud.minewtag.com/apis/esl/label/cascadQuery?page=1&size=60&storeId={self.STORE_ID}&eqstatus=2&type=1", headers=self.tokenHeader)
        return [item['mac'] for item in allTagData.json()['items'] if item['screenSize'] != "29"]

    ######              ######
    # SET METHODS 
    #   updateDeviceBinding(macAddress, templateId) - single display update
    #   updateDeviceBindingBulk(macAddresses, templateId) - update multiple displays to a given template
    #   refreshTagsInBulk(macAddresses) - refresh all tags in array
    #   transferCards(mac1, mac2) - transfer the card in mac1 to mac2 and clear mac1
    #   clearAll(macAddresses) - clear all cards in array
    ######              ######
    count = 0;
    def update_device_binding(self, macAddress, templateId):
        updateDeviceData = {
            "labelMac":macAddress,
            "goodsId": self.DATA_ID,
            "storeId": self.STORE_ID,
            "demoIdMap":{"A":templateId}
        }
        updateDeviceResponse = requests.post("https://cloud.minewtag.com/apis/esl/label/update", 
                                            headers=self.contentTypeAndTokenHeader,
                                            data=json.dumps(updateDeviceData))
        
        response_json = updateDeviceResponse.json()
        print(response_json)
        if response_json.get('code') == 200:
            self.macTemplateDict[macAddress] = templateId
        if response_json.get('code') == 54015:
            self.update_device_binding(macAddress, templateId) #retry
            print("Performing retry")
        return response_json

    # Sets all cards in the macAddresses array to the template with the given templateId
    def updateDeviceBindingBulk(self, macAddresses, templateId):
        for mac in macAddresses:
            self.update_device_binding(mac, templateId)

    def refreshTagsInBulk(self, macAddresses):
        updateTagsInBulkBody = {
        "storeId": self.STORE_ID,
        "macs": macAddresses
        }
        updateTagsInBulkResponse = requests.post("https://cloud.minewtag.com/apis/esl/label/batchBrush",
                                                headers=self.contentTypeAndTokenHeader,
                                                data=json.dumps(updateTagsInBulkBody))
        return updateTagsInBulkResponse.json()  

    def transferCards(self, mac1, mac2):
        self.update_device_binding(mac2, self.macTemplateDict.get(mac1))
        self.clearAll([mac1])
    
    def clearAll(self, macAddresses):
        # Filter out cards that have already been cleared
        alreadyCleared = [macAddress for (macAddress, templateID) in self.macTemplateDict.items() if templateID == self.BLANK_TEMPLATE_ID]
        self.updateDeviceBindingBulk(set(macAddresses) - set(alreadyCleared), self.BLANK_TEMPLATE_ID)
        