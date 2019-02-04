from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from database_setup import Base, Restaurant, MenuItem
from flask import Flask, render_template, request, redirect, url_for, flash, jsonify
from flask import session as login_session
import random, string
from oauth2client.client import flow_from_clientsecrets
from oauth2client.client import FlowExchangeError
import httplib2
import json
from flask import make_response
import requests

CLIENT_ID = json.loads(
	open('client_secrets.json','r').read())['web']['client_id']

app = Flask(__name__)


engine = create_engine('sqlite:///restaurantmenu.db')
Base.metadata.bind = engine
DBSession = sessionmaker(bind=engine)
session = DBSession()


# API Endpoint
@app.route('/restaurants/<int:restaurant_id>/menu/JSON')
def restaurantMenuJSON(restaurant_id):
	restaurant = session.query(Restaurant).filter_by(id = restaurant_id).one()
	items = session.query(MenuItem).filter_by(restaurant_id = restaurant_id).all()
	return jsonify(MenuItems=[i.serialize for i in items])


@app.route('/restaurants/<int:restaurant_id>/menu/<int:menu_id>/JSON/')
def menuItemJSON(restaurant_id, menu_id):
	menuItem = session.query(MenuItem).filter_by(id=menu_id).one()
	return jsonify(MenuItem = menuItem.serialize)


# Home page
@app.route('/')
@app.route('/home')
def HomePage():
	restaurants = session.query(Restaurant).all()
	output = "<html><body>"
	for i in restaurants:
		output += "<a href='/restaurants/{}'>{}</br></a>".format(i.id, i.name)
	output += "</html></body>"
	return output


# New Menu Item Page
@app.route('/restaurant/<int:restaurant_id>/new', methods=['GET', 'POST'])
def NewMenuItem(restaurant_id):
	if 'username' not in login_session:
		return redirect('/login')
	if request.method == 'POST':
		newItem = MenuItem(name=request.form['name'],restaurant_id=restaurant_id)
		session.add(newItem)
		session.commit()
		flash("New Menu Item Created :)")
		return redirect(url_for('RestaurantPage', restaurant_id=restaurant_id))

	else:
		return render_template('newMenuItem.html', restaurant_id=restaurant_id)


# Edit Menu Item Page
@app.route('/restaurant/<int:restaurant_id>/<int:menu_id>/edit', methods=['GET', 'POST'])
def EditMenuItem(restaurant_id, menu_id):
	if 'username' not in login_session:
		return redirect('/login')
	if request.method == 'POST':
		if request.form['newname']:
			currentItem = session.query(MenuItem).filter_by(id = menu_id).one()
			currentItem.name = request.form['newname']
		session.add(currentItem)
		session.commit()
		flash("Menu item has been edited :)")
		return redirect(url_for('RestaurantPage', restaurant_id=restaurant_id))
	else:
		return render_template('editMenuItem.html', 
							 	restaurant=restaurant_id, 
							 	menu_id=menu_id)


# Delete Menu Item Page
@app.route('/restaurant/<int:restaurant_id>/<int:menu_id>/delete', methods=['GET','POST'])
def DeleteMenuItem(restaurant_id, menu_id):
	if 'username' not in login_session:
		return redirect('/login')
	if request.method == 'POST':
		if request.form['removeItem']:
			item = session.query(MenuItem).filter_by(id = menu_id).one()
			session.delete(item)
			session.commit()
			flash("Your menu item has been deleted :( make a new one!")
			return redirect(url_for('RestaurantPage',restaurant_id=restaurant_id))

	else:

		return render_template('deleteMenuItem.html',restaurant_id=restaurant_id,menu_id=menu_id)


@app.route('/login')
def showLogin():
	state = ''.join(random.choice(string.ascii_uppercase + string.digits) for x in range(32))
	login_session['state'] = state
	return render_template('login.html', STATE=state)


# Single Restaurant Page
@app.route('/restaurants/<int:restaurant_id>/')
def RestaurantPage(restaurant_id):
	restaurant = session.query(Restaurant).filter_by(id = restaurant_id).one()
	MenuItems = session.query(MenuItem).filter_by(restaurant_id = restaurant.id)
	return render_template('menu.html', restaurant=restaurant, items=MenuItems)


@app.route('/gconnect', methods=['POST'])
def gconnect():
	print('entered gconnect function')
	# confirm that the token sent from the server, is the
	# same token that the client sent to the server
	if request.args.get('state') != login_session['state']:
		response = make_response(json.dumps('Invalid state parameters'), 401)
		response.headers['Content-Type'] = 'application/json'
		return response

	# get the one time code from the server
	code = request.data
		
	# now we want to try to use the one time code and exchange
	# it for a credentials object which contains the access token from our server
	try:
		# place the client_secrets.json file contents into oauth_flow
		oauth_flow = flow_from_clientsecrets('client_secrets.json', scope='')

		# specify with 'postmessage' that this is the one time code flow
		# that my server will be sending off
		# In other words, add 'postmessage' to be like, yeah this is the
		# one I want to use
		# Similar to staging something
		oauth_flow.redirect_uri = 'postmessage'

		# Now we basically just need to commit everything on the oauth_flow
		# and pass in the one time code that we got earlier from request.data
		credentials = oauth_flow.step2_exchange(code) #this method exchanges an authorization code for a credentials object

		# if all goes well then the response from google will be this
		# credentials object

	# Handle the error if something goes wrong in these steps
	except FlowExchangeError:
		reponse = make_response(json.dumps('Failed to upgrade the authorization code.'),401)
		response.headers['content-type'] = 'application/json'
		return response

	# So now that we have this credentials object, we need to check to see
	# if there is a valid access token inside of it
	access_token = credentials.access_token

	# So now we just verify that access token by sending a GET request
	# to google via the httplib2 library. First we create a url and pass
	# in the token as a query parameter
	url = 'https://www.googleapis.com/oauth2/v1/tokeninfo?access_token={}'.format(access_token)

	# now create a handle to a request object
	h = httplib2.Http()

	# And send that off to verify
	result = json.loads(h.request(url, 'GET')[1])

	# Ok so now we've sent off our access token to be verified and stored the 
	# response from google in an object called 'result'

	# So basically now all we have to do is verify that everything matches 
	# and we're good to go

	# So now we need to make sure that result has no errors, and if it does,
	# send a 500 internal error response
	if result.get('error') is not None:
		# dump the error to the client in json format
		response = make_response(json.dumps(result.get('error')), 500)
		response.headers['content-type'] = 'application/json'
		return response

	# Verify user's token id 
	gplus_id = credentials.id_token['sub']
	if result['user_id'] != gplus_id:
		response = make_response(
			json.dumps("Token's user ID doesn't match given user ID."),401)
		response.headers['content-type'] = 'application/json'
		return response

	# Verify that the access token is for THIS app
	if result['issued_to'] != CLIENT_ID:
		response = make_response(
			json.dumps("Token's client ID does not match app's client id"), 401)
		response.headers['content-type'] = 'application/json'
		return response

	# Check to see if the user is already logged into the system
	stored_credentials = login_session.get('credentials')
	stored_gplus_id = login_session.get('gplus_id')
	if stored_credentials is not None and gplus_id == stored_gplus_id:
		response = make_response(json.dumps('Current user is already connected.'),200)
		response.headers['content-type'] = 'applcation/json'
		return response

	# Now store the access token in the session for later use
	login_session['access_token'] = credentials.access_token
	login_session['gplus_id'] = gplus_id

	# Now use the googleplus api to get more info about the user
	userinfo_url = "https://www.googleapis.com/oauth2/v1/userinfo"

	# create a parameters object for the request
	params = {'access_token': credentials.access_token, 'alt':'json'}

	# make the request and store it in 'answer'
	answer = requests.get(userinfo_url,params=params)

	# convert the answer into a json object
	data = answer.json()

	# now store the data returned from google in login_session
	login_session['username'] = data['name']
	login_session['picture'] = data['picture']
	login_session['email'] = data['email']

	# create a flash message that lets the user know that they are logged in
	flash('You are now logged in as {}'.format(login_session['username']))

	# Create an output that displays the username and stuff
	output = '<h1>Welcome, '
	output += login_session['username']
	output += '!</h1>'
	output += '<img src="'
	output += login_session['picture']
	output += '" style="width:300px;height:300px;border-radius:150px;-webkit-border-radius:150px;-moz-border-radius:150px;">'
	print('Complete')
	return output


# Logout route
@app.route('/gdisconnect')
def gdisconnect():

	# First we want to check to make sure that they're actually logged in
	access_token = login_session.get('access_token')
	if access_token is None:
		response = make_response(json.dumps('Current user is not connected.'),401)
		response.headers['content-type'] = 'application/json'
		return response

	# Now the way that we log out is we revoke access tokens
	# To do that we send an api call to google's revoke-token uri
	url = 'https://accounts.google.com/o/oauth2/revoke?token={}'.format(access_token)
	h = httplib2.Http()
	result = h.request(url,'GET')[0]

	# So let's handle the response from google to revoke the token
	if result['status'] == '200':
		# Reset user's session
		del login_session['access_token']
		del login_session['gplus_id']
		del login_session['username']
		del login_session['email']
		del login_session['picture']

		# And send the response that acknowledges that we have successfully revoked the
		# access token
		response = make_response(json.dumps('Successfully disconnected.'),200)
		response.headers['content-type'] = 'application/json'
		return response

	else:
		# If we get any response other than a 200, then we know something went wrong
		# and that we need to handle that error.
		response = make_response(json.dumps('Error disconnecting user. Failed to revoke access token.'),400)
		response.headers['content-type'] = 'application/json'
		return response


if __name__ == '__main__':
	app.secret_key = 'super_secret_key'
	port = 5001
	app.debug = True
	app.run(host = '0.0.0.0', port = port)
	print 'Server started on port {}'.format(port)