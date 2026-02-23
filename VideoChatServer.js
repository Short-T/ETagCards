const express = require('express');

//Default port for the TCP side of the server
const port = 9900;

//Default port for the UDP side of the server
const udpport = 9901;

//Initialize the Express server
const app = express();

//Get the sqlite3 package
var sqlite3 = require('sqlite3').verbose();

//Load the database (if it exists)
var db = new sqlite3.Database('testdb');

/*
	Root endpoint (simple welcome message)
*/
app.get('/', function(req, res){
  return res.send('Welcome to the app!');
});

/*
	Creates a new user from a username and a name (sets a default IP, as well as the login state to false)
	@param		username: 	the user's desired username
	@param		name:			the user's desired display name
	
	@return 	{type:'success', message:'User created'}
*/
app.get('/users/create', function(req, res){
  let query = "INSERT INTO users (username, name, ip_address, logged_in) VALUES ('" + req.query.username + "', '" + req.query.name + "', '0.0.0.0', FALSE)";
  let condition = "SELECT * FROM users WHERE username = '" + req.query.username  + "';";
  
  db.serialize(function(){
	 db.all(condition, function(err, rows){
		 if(rows.length == 0){
			 // console.log(query);
			db.run(query);
			console.log("User created");
			showTables();
			return res.send("{type:'success', message:'User created'}");
		 }else{
			return res.send("{type:'error', message:'User already exists'}");
		 }
	 });
    
  });

 
});

/*
	Logs in a user using their username (and finds out their IP from the connection object)
	@param		username:	the user's inputted username
	
	@return		{type: 'success', message: '', data: {userId: %UserID% }}
					OR
					{type: 'error', message: 'User does not exist', data: {}} 
*/
app.get('/users/login', function(req,res){
	let ip = req.headers['x-forwarded-for'] || req.connection.remoteAddress;
	console.log(req.connection);
	ip = ip.substring(ip.lastIndexOf(":") + 1, ip.length);
	let query = "UPDATE users SET ip_address = '" + ip + "', logged_in = TRUE WHERE username = '" + req.query.username + "';";
	let condition = "SELECT user_id FROM users WHERE username = '" + req.query.username + "';";
	db.all(condition, function(err, rows){
		if(rows.length > 0){
			// console.log(query);
			db.serialize(function(){
				db.run(query);
				console.log("User logged in");
				showTables();
				return res.send("{type: 'success', message: '', data: {userId: " + rows[0].user_id + "}}");
			});
		}else{
			return res.send("{type: 'error', message: 'User does not exist', data: {}}");
		}
	});
});

/*
	Logs out a user using their username (sets their login state to false)
	@param		username:	the user's inputted username
	
	@return		{type: 'success', message: 'User logged out'}
*/
app.get('/users/logout', function(req,res){
	let query = "UPDATE users SET logged_in = FALSE WHERE username = '" + req.query.username + "';";
	// console.log(query);
	db.serialize(function(){
		db.run(query);
		console.log("User logged out");
		showTables();
	});
	
	return res.send("{type:'success', message:'User logged out'}");
});

/*
	Retrieves information about a specific user
	@param		username:			the desired user's username
	
	@return		{type: 'error', message: 'User does not exist', data:{}}
						OR
						{type: 'success', message: '', data:{ % USER DATA % }}
*/
app.get('/users/user', function(req, res){
	let query = "SELECT username, name FROM users WHERE user_id = " + req.query.userId + ";";
	// console.log(query);
	db.all(query, function(err, rows){
		if(rows.length > 0){
			let temp = {};
			temp.type = 'success';
			temp.message = '';
			temp.data = rows[0];
			return res.send(JSON.stringify(temp));
		}else{
			return res.send("{type: 'error', message: 'User does not exist', data:{}}");
		}
	});
});

/*
	Retrieves list of all users
	@param		username:			the desired user's username
	
	@return		{type: 'error', message: 'User does not exist', data:{}}
						OR
						{type: 'success', message: '', data:{ % USER DATA % }}
*/
app.get('/users', function(req, res){
	let query = "SELECT username from users";
	db.serialize(function(){
		db.all(query, function(err, rows){
			let result = {};
				result.type = 'success';
				result.message = '';
			if(rows.length > 0){
				result.data = rows;
				return res.send(JSON.stringify(result));
			}else{
				result.data = [];
				return res.send(JSON.stringify(result));
			}
		});
		showTables();
	});
});

/*
	Retrieves the list of contacts for a specific user
	@param		userId:			the desired user's ID
	
	@return {type: 'success', message:' ', data: [ %UserContacts% ]}
*/
app.get('/contacts/user', function(req, res){
	let query = "SELECT * FROM (SELECT contact_user_id from contacts where (user_id = " + req.query.userId + ") UNION SELECT user_id from contacts where (contact_user_id = " + req.query.userId + ")) AS A INNER JOIN (SELECT user_id, name FROM users) AS B ON A.contact_user_id = B.user_id;";
	// console.log(query);
	db.serialize(function(){
		db.all(query, function(err, rows){
			let result = {};
				result.type = 'success';
				result.message = '';
			if(rows.length > 0){
				result.data = rows;
				return res.send(JSON.stringify(result));
			}else{
				result.data = [];
				return res.send(JSON.stringify(result));
			}
		});
		showTables();
	});
});

/*
	Add a contact to a user's contacts list
	@param		userId:			the user's ID
	@param		contactId:	the contact's ID (that is to be added to the user's list)
	
	@return 		{type: 'success', message:'Contact added'}
						OR
						{type: 'error', message:'Contact already exists'}
*/
app.get('/contacts/add', function(req, res){
	let query = "INSERT INTO contacts (user_id, contact_user_id) VALUES (" + req.query.userId + ", " + req.query.contactId + ");";
	// console.log(query);
	let condition = "SELECT * FROM contacts WHERE (user_id = " + req.query.userId + " AND contact_user_id = " + req.query.contactId + ") OR (user_id = " + req.query.contactId + " AND contact_user_id = " + req.query.userId + ");";
	
	db.all(condition, function(err, rows){
		if(rows.length === 0){
			db.serialize(function(){
				db.run(query);
				console.log("Contact added");
				showTables();
			});
			return res.send("{type: 'success', message:'Contact added'}");
		}else{
			return res.send("{type: 'error', message:'Contact already exists'}");
		}
	});
});

/*
	Remove the contact from a user's contacts list
	@param			userId:		the user's ID
	@param 		contactId:	the contact's ID (that is to be removed from the user's list)
	
	@return		{type:'success', message: 'Contact removed'}
*/
app.get('/contacts/remove', function(req, res){
	let query = "DELETE FROM contacts WHERE (user_id = " + req.query.userId + " AND contact_user_id = " + req.query.contactId + ") OR (user_id = " + req.query.contactId + " AND contact_user_id = " + req.query.userId + ");";
	// console.log(query);
	db.serialize(function(){
		db.run(query);
		console.log("Contact removed");
		showTables();
	});
	
	return res.send("{type:'success', message: 'Contact removed'}");
});

/*
	Retrieves a user's list of incoming contact requests
	@param		userId:			the user's ID
	
	@return 		{type: 'success', message: '', data: [ %UserContactRequests% ]}
*/
app.get('/contacts/requests/user', function(req, res){
	let query = "SELECT A.sender_id, B.name FROM contact_requests AS A INNER JOIN (SELECT * FROM users) AS B ON A.sender_id = B.user_id WHERE A.receiver_id = " + req.query.userId + ";";
	// console.log(query);
	db.serialize(function(){
		db.all(query, function(err, rows){
			let result = {};
			result.type = 'success';
			result.message = '';
			if(rows.length > 0){
				result.data = rows;
				return res.send(JSON.stringify(result));
			}else{
				result.data = [];
				return res.send(JSON.stringify(result));
			}
		});
	});
});

/*
	Sends a contact request to another user
	@param		userId:			the user's ID (who is sending the request)
	@param		username:	the contact's username (who is receiving the request)
	
	@return		{type:'success', message:'Contact request added'}
*/
app.get('/contacts/requests/add', function(req, res){
	let contactCheck = "SELECT * FROM users WHERE username = '" + req.query.username + "';";
	
	db.all(contactCheck, function(err, rows){
		if(rows.length > 0){
			let contactId = rows[0].user_id;
			let query = "INSERT INTO contact_requests (sender_id, receiver_id) VALUES (" + req.query.userId + ", " + contactId + ");";
			let condition = "SELECT * FROM contact_requests WHERE (sender_id = " + req.query.userId + " AND receiver_id = " + contactId + ") OR (sender_id = " + contactId + " AND receiver_id = " + req.query.userId + ");";
			let condition2 = "SELECT * FROM contacts WHERE (user_id = " + req.query.userId + " AND contact_user_id = " + contactId + ") OR (user_id = " + contactId + " AND contact_user_id = " + req.query.userId + ");";
			// console.log(query);	
			db.all(condition, function(err, rows){
				if(rows.length === 0){
					db.all(condition2, function(err, rows2){
						if(rows2.length === 0){
							db.serialize(function(){
								db.run(query);
								console.log("Contact request added");
								showTables();
							});
						}
					});
				}
			});
		}
	});
	
	return res.send("{type:'success', message:'Contact request added'}");
});

/*
	Cancels a sent contact request that was sent to another user (the receiving user declines the request)
	@param		userId:			the user's ID (who is receiving the request)
	@param		contactId:	the contact's ID (who is sending the request)
	
	@return		{type:'success', message:'Contact request removed'}
*/
app.get('/contacts/requests/remove', function(req, res){
	let query = "DELETE FROM contact_requests WHERE receiver_id = " + req.query.userId + " AND sender_id = " + req.query.contactId + ";";
	// console.log(query);
	db.serialize(function(){
		db.run(query);
		console.log("Contact request removed");
		showTables();
	});
	
	return res.send("{type:'success', message:'Contact request removed'}");
});

/*
	Accepts a received contact request (removes the request and adds the sending user to the receiving user's contacts list)
	@param		userId:			the user's ID (who is receiving the request)
	@param		contactId:	the contact's ID (who is sending the request)
	
	@return		{type:'success', message:'Contact request accepted'}
						OR
						{type:'error', message:'Contact request does not exist'}
*/
app.get('/contacts/requests/accept', function(req, res){
	let condition = "SELECT * FROM contact_requests WHERE (sender_id = " + req.query.userId + " AND receiver_id = " + req.query.contactId + ") OR (sender_id = " + req.query.contactId + " AND receiver_id = " + req.query.userId + ");";

	db.all(condition, function(err, rows){
		if(rows.length > 0){
			db.serialize(function(){
				db.run("INSERT INTO contacts (user_id, contact_user_id) VALUES (" + req.query.userId + ", " + req.query.contactId + ");");
				db.run("DELETE FROM contact_requests WHERE (sender_id = " + req.query.userId + " AND receiver_id = " + req.query.contactId + ") OR (sender_id = " + req.query.contactId + " AND receiver_id = " + req.query.userId + ");");
				console.log("Contact request accepted");
				showTables();
				return res.send("{type:'success', message:'Contact request accepted'}");
			});
		}else{
			return res.send("{type:'error', message:'Contact request does not exist'}");
		}
	});
	
});

/*
	Adds a session between two users
	@param		userId:			the user's ID (one side of the session)
	@param		contactId:	the contact's ID (other side of the session)
	
	@return		{type:'success', message:'Session added'}
						OR
						{type:'error', message:'Session already exists'}
*/
app.get('/sessions/add', function(req, res){
	let query = "INSERT INTO sessions (sender_id, receiver_id) VALUES (" + req.query.userId + ", " + req.query.contactId + ");";
	let condition = "SELECT * FROM sessions WHERE (sender_id = " + req.query.userId + " AND receiver_id = " + req.query.contactId + ") OR (sender_id = " + req.query.contactId + " AND receiver_id = " + req.query.userId + ");";
	// console.log(query);
	db.serialize(function(){
		db.all(condition, function(err, rows){
			if(rows.length === 0){
				db.run(query);
				console.log("Session added");
				showTables();
				
				db.run("DELETE FROM session_requests WHERE (sender_id = " + req.query.userId + " AND receiver_id = " + req.query.contactId + ") OR (sender_id = " + req.query.contactId + " AND receiver_id = " + req.query.userId + ");");
				
				return res.send("{type:'success', message:'Session added'}");
				
			}else{
				return res.send("{type:'error', message:'Session already exists'}");
			}
		});
	});
});

/*
	Removes an existing session between two users
	@param		userId:			the user's ID (one side of the session)
	@param		contactId:	the contact's ID (other side of the session)

	@return		{type:'success', message: 'Session removed'}
*/
app.get('/sessions/remove', function(req, res){
	let query = "DELETE FROM sessions WHERE (sender_id = " + req.query.userId + " AND receiver_id = " + req.query.contactId + ") OR (sender_id = " + req.query.contactId + " AND receiver_id = " + req.query.userId + ");";
	// console.log(query);
	db.serialize(function(){
		db.run(query);
		console.log("Session removed");
		showTables();
		
		db.get("SELECT ip_address AS ip FROM users WHERE user_id = " + req.query.userId + ";", function(err, row){
			for(let i=0;i<sessions.length;i++){
				if(sessions[i].host === row.ip || sessions[i].client === row.ip){
					sessions.splice(i,1);
				}
			}
		});
	});
	
	return res.send("{type:'success', message: 'Session removed'}");
});

/*
	Returns the current session of a user
	@param		userId:			the user's ID (one side of the session)
	@param		contactId:		the contact's ID (other side of the session)
	
	@return		{type:'success', message:'', data: { %SessionData% }}
						OR
						{type:'error', message:'No sessions found'}
*/
app.get('/sessions/user', function(req, res){
	let query = "SELECT * FROM sessions WHERE sender_id = " + req.query.userId + " AND receiver_id = " + req.query.contactId + ";";
	// console.log(query);
	db.all(query, function(err, rows){
		if(rows.length > 0){
			let temp = {};
			temp.type = 'success';
			temp.message = '';
			temp.data = rows[0];
			return res.send(JSON.stringify(temp));
		}else{
			return res.send("{type:'error', message:'No sessions found'}");
		}
	});
});

/*
	Sends a session request to another user
	@param		userId:			the user's ID (who is sending the request)
	@param		contactId:	the contact's ID (who is receiving the request)
	
	@return		{type:'success', message:'Session request added'}
						OR
						{type:'error', message:'Session request already exists'}
						OR
						{type:'error', message:'Session already exists'}
*/
app.get('/sessions/requests/add', function(req, res){
	let query = "INSERT INTO session_requests (sender_id, receiver_id, is_accepted) VALUES (" + req.query.userId + ", " + req.query.contactId + ", 0);";
	let condition = "SELECT * FROM sessions WHERE (sender_id = " + req.query.userId + " AND receiver_id = " + req.query.contactId + ") OR (sender_id = " + req.query.contactId + " AND receiver_id = " + req.query.userId + ");";
	let condition2 = "SELECT * FROM session_requests WHERE (sender_id = " + req.query.userId + " AND receiver_id = " + req.query.contactId + ") OR (sender_id = " + req.query.contactId + " AND receiver_id = " + req.query.userId + ");";
	// console.log(query);
	db.all(condition, function(err,  rows){
		if(rows.length === 0){
			db.all(condition2, function(err, rows2){
				db.serialize(function(){
					db.run("DELETE FROM session_requests WHERE sender_id = " + req.query.userId + " OR receiver_id = " + req.query.contactId + ";");
					db.run("DELETE FROM sessions WHERE sender_id = " + req.query.userId + " OR receiver_id = " + req.query.contactId + ";");
					db.run(query);
					console.log("Session request added");
					showTables();
					
					db.all("SELECT ip_address AS ip, user_id FROM users WHERE user_id = " + req.query.userId + " OR user_id = " + req.query.contactId + ";", function(err, rows2){
					    // Check errors
						if (err) {
						  console.error("DB error:", err);
						  return res.send("{type:'error', message:'Database error'}");
						}
						// Validate row count
						if (!rows2 || rows2.length < 2) {
						  console.error("Not enough users found for session:", rows2);
						  return res.send("{type:'error', message:'User(s) not found'}");
						}
						// Sort rows so host is always the sender
						rows2.sort((a, b) => {
						  if (a.user_id == req.query.userId) return -1;
						  return 1;
						});

						let newSession = {};
						newSession.host = rows2[0].ip;
						newSession.client = rows2[1].ip;
						newSession.hostId = rows2[0].user_id;
						newSession.clientId = rows2[1].user_id;
						newSession.hostPort = -1;
						newSession.clientPort = -1;
						sessions.push(newSession);
						return res.send("{type:'success', message:'Session request added'}");
					});
				});
			});
			
		}else{
			return res.send("{type:'error', message:'Session already exists'}");
		}
	});
});

/*
	Removes an existing session request that was sent to a user
	@param		userId:			the user's ID (one side of the session)
	@param		contactId:	the contact's ID (other side of the session)
	
	@return		{type:'success', message:'Session request removed'}
*/
app.get('/sessions/requests/remove', function(req, res){
	let query = "DELETE FROM session_requests WHERE (sender_id = " + req.query.userId + " AND receiver_id = " + req.query.contactId + ") OR (sender_id = " + req.query.contactId + " AND receiver_id = " + req.query.userId + ");";
	// console.log(query);
	db.serialize(function(){
		db.run(query);
		console.log("Session request removed");
		showTables();
		
		db.get("SELECT ip_address AS ip FROM users WHERE user_id = " + req.query.userId + ";", function(err, row){
			for(let i=0;i<sessions.length;i++){
				if(sessions[i].host === row.ip || sessions[i].client === row.ip){
					sessions.splice(i,1);
				}
			}
		});
	});
	
	return res.send("{type:'success', message:'Session request removed'}");
});

/*
	Accepts an existing session requests (and begins the session)
	@param		userId:			the user's ID (who is receiving the request)
	@param		contactId:	the contact's ID (who is sending the request)
	
	@return		{type:'success', message:'Session request accepted'}
						OR
						{type:'error', message:'Seesion request does not exist'}
*/
app.get('/sessions/requests/accept', function(req, res){
	let condition = "SELECT * FROM session_requests WHERE  (sender_id = " + req.query.userId + " AND receiver_id = " + req.query.contactId + ") OR (sender_id = " + req.query.contactId + " AND receiver_id = " + req.query.userId + ");";
	
	db.all(condition, function(err, rows){
		if(rows.length > 0){
			db.serialize(function(){
				db.run("UPDATE session_requests SET is_accepted = 1 WHERE (sender_id = " + req.query.userId + " AND receiver_id = " + req.query.contactId + ") OR (sender_id = " + req.query.contactId + " AND receiver_id = " + req.query.userId + ");");
				//db.run("INSERT INTO sessions (sender_id, receiver_id) VALUES (" + req.query.userId + ", " + req.query.contactId + ");");
				console.log("Session request accepted");
				showTables();
				return res.send("{type:'success', message:'Session request accepted'}");
			});
		}else{
			return res.send("{type:'error', message:'Session request does not exist'}");
		}
	});
});

/*
	Retrieves all session requests sent to a specific user
	@param		userId:			the user's ID (who is receiving the requests)
	
	@return		{type: 'success', message: '', data: [ %UserSessionRequests% ]}
*/
app.get('/sessions/requests/user', function(req, res){
	let query = "SELECT A.sender_id AS user_id, A.is_accepted, B.name FROM session_requests AS A INNER JOIN (SELECT * FROM users) AS B ON A.sender_id = B.user_id WHERE receiver_id = " + req.query.userId + ";";
	// console.log(query);
	db.serialize(function(){
		db.all(query, function(err, rows){
			if (rows != null)
				if (rows.length > 0){
					let temp = {};
					temp.type = 'success';
					temp.message = '';
					temp.data = rows[0];
					return res.send(JSON.stringify(temp));
				}else{
					return res.send("{type:'error', message:'no session requests found'}");
				}
		});
	});
});

app.get('/vumark/data/get', function(req, res){
    let query = "SELECT * FROM vumark_data WHERE (sender_id = " + req.query.userId + " AND receiver_id = " + req.query.contactId + ") OR (sender_id = " + req.query.contactId + " AND receiver_id = " + req.query.userId + ");";
    // console.log(query);
    db.all(query, function(err, rows){
        if(rows.length > 0){
            let temp = {};
            temp.type = 'success';
            temp.message = '';
            temp.data = rows[0];
            return res.send(JSON.stringify(temp));
        }else{
            return res.send("{type:'error', message:'no vumark data found'}");
        }
    });
});

app.get('/vumark/data/update', function(req, res){
    let query = "SELECT * FROM vumark_data WHERE (sender_id = " + req.query.userId + " AND receiver_id = " + req.query.contactId + ") OR (sender_id = " + req.query.contactId + " AND receiver_id = " + req.query.userId + ");";
    // console.log(query);
    db.all(query, function(err, rows){
        if(rows.length === 0){
            db.run("INSERT INTO vumark_data (sender_id, receiver_id, selected_cards, discard_card_id, restart_flag, sender_cards, receiver_cards) VALUES (" + req.query.userId + ", " + req.query.contactId + ", " + req.query.selectedCards + ", " + req.query.discardCardId + ", " + req.query.restart_flag + ", " + req.query.userCards + ", " + req.query.receiverCards + ")");
            console.log("inserted vuMark data");
            showTables();
            return res.send("{type:'success', message:'inserted vuMark data'}");
        }else if(rows.length > 0){
			let restart_flag = rows[0].restart_flag.toString();
			let user_id = req.query.userId;

			if(restart_flag !== "0"){
				if(user_id === restart_flag){
					return res.send("{type:'success', message:'updated vuMark data'}");
				}
				else if(user_id !== restart_flag && req.query.selectedCards !== "\"\""){
					return res.send("{type:'success', message:'restart game'}");
				}
			}
            
            if(Number(req.query.userId) === rows[0].sender_id){
                db.run("UPDATE vumark_data SET sender_cards = " + req.query.userCards + " WHERE (sender_id = " + req.query.userId + " AND receiver_id = " + req.query.contactId + ") OR (sender_id = " + req.query.contactId + " AND receiver_id = " + req.query.userId + ");");
            } else {
                db.run("UPDATE vumark_data SET receiver_cards = " + req.query.userCards + " WHERE (sender_id = " + req.query.userId + " AND receiver_id = " + req.query.contactId + ") OR (sender_id = " + req.query.contactId + " AND receiver_id = " + req.query.userId + ");");
            }

            db.run("UPDATE vumark_data SET selected_cards = " + req.query.selectedCards + ", discard_card_id = " + req.query.discardCardId + ", restart_flag = " + req.query.restart_flag + " WHERE (sender_id = " + req.query.userId + " AND receiver_id = " + req.query.contactId + ") OR (sender_id = " + req.query.contactId + " AND receiver_id = " + req.query.userId + ");");
            console.log("updated vuMark data");
            showTables();
            return res.send("{type:'success', message:'updated vuMark data'}");
        }
    });
});

app.get('/vumark/data/remove', function(req, res){
    let query = "SELECT * FROM vumark_data WHERE (sender_id = " + req.query.userId + " AND receiver_id = " + req.query.contactId + ") OR (sender_id = " + req.query.contactId + " AND receiver_id = " + req.query.userId + ");";
    // console.log(query);
    db.all(query, function(err, rows){
        if(rows.length === 0){
            return res.send("{type:'error', message:'no vuMark data found'}");
        }else{
            db.run("DELETE FROM vumark_data WHERE (sender_id = " + req.query.userId + " AND receiver_id = " + req.query.contactId + ") OR (sender_id = " + req.query.contactId + " AND receiver_id = " + req.query.userId + ");");
            showTables();
            return res.send("{type:'success', message:'deleted vuMark data'}");
        }
    });
});



/*
	Binds the server to the specified port
*/
app.listen(port, () => {
	console.log('------------------------------------------------------');
	console.log('Application listening on port ' + port);
	console.log('------------------------------------------------------');
	initDB();
});


/*
	This marks the start of the UDP side of the server
*/

//Session objects (each index holds an object that contains two clients, with each of their IPs and ports)
var sessions = [];

//Request the UDP datagram package (to send and receive packets)
var dgram = require('dgram');

//Create the datagram socket using udp4
var udpserver = dgram.createSocket('udp4');

//This is called when the server is first started (shows information about it)
udpserver.on('listening', function(){
  var address = udpserver.address();
  console.log('UDP Server listening on ' + address.address + ':' + address.port);
  console.log('UDP Server has a receiving buffer of ' + udpserver.getRecvBufferSize() + ' bytes and a sending buffer of ' + udpserver.getSendBufferSize());
});

//This is called whenever the server receives a UDP datagram from any client
udpserver.on('message', function(message, remote){
	
	//Print out details about the message (sender's IP address and port, message length)
	//console.log(remote.address + ':' + remote.port + ' - Received Packet of length ' + message.length);
	
	//If the length is smaller than 5 bytes, it is considered an "empty" packet
	//These are used to record the sender's ip and port (so we can send them the appropriate information later)
	//Clients should only send a few of these packets at the very start of the video call, to "tell" the server what their information is
	if(message.length <= 5){
		//Get the ID number from the packet
		let id = message.readUInt32BE(0);
		
		//Go through existing sessions, and put the message's information into the relevant session (based on ID above)
		for(let i=0;i<sessions.length;i++){
			console.log(sessions[i] + ", " + id);
			if(sessions[i].hostId === id){
				sessions[i].hostPort = remote.port;
			}else if(sessions[i].clientId === id){
				sessions[i].clientPort = remote.port;
			}
		}
	}else{
		for(let i=0;i<sessions.length;i++){
			if(remote.address === sessions[i].host && sessions[i].hostPort === remote.port && sessions[i].clientPort != -1){
				udpserver.send(message, 0, message.length, sessions[i].clientPort, sessions[i].client);
				//  console.log("Sent packet to " + sessions[i].clientPort);
				break;
			}else if(remote.address == sessions[i].client && sessions[i].clientPort === remote.port && sessions[i].hostPort != -1){
				udpserver.send(message, 0, message.length, sessions[i].hostPort, sessions[i].host);
				//  console.log("Sent packet to " + sessions[i].hostPort);
				break;
			}
		}
	}
  
});

udpserver.bind(udpport);

// Functions

/*
	Initializes the database tables
	If they already exist, this does not create the tables again (they get loaded from the database instead).
	Finishes by printing out the contents of all tables
*/
function initDB(){
	db.serialize(function(){
		db.run("CREATE TABLE IF NOT EXISTS users (user_id INTEGER PRIMARY KEY AUTOINCREMENT, username VARCHAR(45) NOT NULL, name VARCHAR(45) NOT NULL, ip_address VARCHAR(45) NOT NULL, logged_in BOOL NOT NULL);");
		console.log("Created/Loaded users table");
		db.run("CREATE TABLE IF NOT EXISTS contacts (contact_id INTEGER PRIMARY KEY AUTOINCREMENT, user_id INTEGER, contact_user_id INTEGER);");
		console.log("Created/Loaded contacts table");
		db.run("CREATE TABLE IF NOT EXISTS contact_requests (request_id INTEGER PRIMARY KEY AUTOINCREMENT, sender_id INTEGER, receiver_id INTEGER);");
		console.log("Created/Loaded contact requests table");
		db.run("CREATE TABLE IF NOT EXISTS sessions (session_id INTEGER PRIMARY KEY AUTOINCREMENT, sender_id INTEGER, receiver_id INTEGER);");
		console.log("Created/Loaded sessions table");
		db.run("CREATE TABLE IF NOT EXISTS session_requests (request_id INTEGER PRIMARY KEY AUTOINCREMENT, sender_id INTEGER, receiver_id INTEGER, is_accepted INTEGER);");
		console.log("Created/Loaded session requests table");
        db.run("CREATE TABLE IF NOT EXISTS vumark_data (data_id INTEGER PRIMARY KEY AUTOINCREMENT, sender_id INTEGER, receiver_id INTEGER, selected_cards VARCHAR, discard_card_id INTEGER, restart_flag INTEGER, sender_cards INTEGER, receiver_cards INTEGER);");
		console.log("Created/Loaded vumark_data table");
        showTables();
	});
}

/*
	Prints out the contents of all tables in the database
*/
function showTables(){
	
	console.log('------------------------------------------------------');
	console.log("TABLES");
	
	let printUsers = function(){
		db.serialize(function(){
			//Print users table
			console.log("USERS TABLE:");
			db.each("SELECT * FROM users", function(err, row){
			  console.log(row.user_id + "\t\t" + row.username + "\t\t" + row.name + "\t\t" + row.ip_address + "\t\t" + row.logged_in);
			}, printContacts);
		});
	};
	
	let printContacts = function(){
		//Print contacts table
		console.log("CONTACTS TABLE:");
		db.each("SELECT * FROM contacts", function(err, row){
		  console.log(row.contact_id + "\t\t" + row.user_id + "\t\t" + row.contact_user_id);
		}, printContactRequests);
	};
	
	let printContactRequests = function(){
		//Print contact requests table
		console.log("CONTACT REQUESTS TABLE:");
		db.each("SELECT * FROM contact_requests", function(err, row){
		  console.log(row.request_id + "\t\t" + row.sender_id + "\t\t" + row.receiver_id);
		}, printSessions);
	};
	
	let printSessions = function(){
		//Print sessions table
		console.log("SESSIONS TABLE:");
		db.each("SELECT * FROM sessions", function(err, row){
		  console.log(row.session_id + "\t\t" + row.sender_id + "\t\t" + row.receiver_id);
		}, printSessionRequests);
	};
	
	let printSessionRequests = function(){
		//Print session requests table
		console.log("SESSION REQUESTS TABLE:");
		db.each("SELECT * FROM session_requests", function(err, row){
		  console.log(row.request_id + "\t\t" + row.sender_id + "\t\t" + row.receiver_id + "\t\t" + row.is_accepted);
		}, printVuMarkData);
	};

    let printVuMarkData = function(){
        //Print session requests table
        console.log("VUMARK DATA TABLE:");
        db.each("SELECT * FROM vumark_data", function(err, row){
          console.log(row.sender_id + "\t\t" + row.receiver_id + "\t\t" + row.selected_cards + "\t\t" + row.discard_card_id + "\t\t" + row.restart_flag + "\t\t" + row.sender_cards + "\t\t" + row.receiver_cards);
        }, stopPrint);
    };
	
	let stopPrint = function(){
		console.log("ACTIVE SESSIONS:");
		console.log(sessions);
		console.log('------------------------------------------------------');
	};
	
	printUsers();
	
}


