from BaseHTTPServer import BaseHTTPRequestHandler, HTTPServer
import cgi
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from database_setup import Base, Restaurant, MenuItem
import os

engine = create_engine('sqlite:///restaurantmenu.db')
Base.metadata.bind = engine
DBSession = sessionmaker(bind=engine)

def getRestaurants():
    session = DBSession()
    restaurantNames = session.query(Restaurant).all()
    return restaurantNames


def createNewRestaurant(rName):
    session = DBSession()
    newEntry = Restaurant(name=rName)
    session.add(newEntry)
    session.commit()


def editRestaurant(rID, newName):
    session = DBSession()
    restaurant = session.query(Restaurant).filter_by(id = rID).one()
    restaurant.name = newName
    session.add(restaurant)
    session.commit()

class WebServerHandler(BaseHTTPRequestHandler):

    def do_GET(self):

        def validEditRequest(path):
            rest = getRestaurants()
            IDs = []
            for restaurant in rest:
                IDs.append('restaurants/{}/new'.format(restaurant.id))
            if path in IDs:
                return True
            else:
                return False

        if self.path.endswith("/restaurants"):
            self.send_response(200)
            self.send_header('content-type', 'text/html')
            self.end_headers()

            restaurantNames = getRestaurants()
            output = "<html><body><a href='/create-restaurant'><h1>Create New Restaurant</h1></a>"
            output += "<h1>Restaurants</h1></br>"
            for restaurant in restaurantNames:
                name = restaurant.name
                output += "<p>{}</p>".format(name)
                output += "<p><a href='/{}/edit'>Edit</a></br>".format(restaurant.id)
                output += "<a href='/confirm-delete'>Delete</a></p>"
            output += "</body></html>"

            self.wfile.write(output)

        elif self.path.endswith("/create-restaurant"):
            self.send_response(200)
            self.send_header("Location", "/create-restaurant")
            self.send_header("Content-type", "text/html")
            self.end_headers()

            output = "<html><body>"
            output += "<h1>Create New Restaurant</h1>"
            output += "<form method='POST' enctype='multipart/form-data'><input type='text' name='restaurant'></br>"
            output += "<input type='submit' value='Submit'></form>"

            self.wfile.write(output)

        elif self.path.endswith('/edit'):
            self.send_response(200)
            self.send_header('location', self.path)
            self.send_header('content-type', 'text/html')
            self.end_headers()

            output = "<html><body>"
            output += "<h1>Edit Restaurant Name</h1>"
            output += "<form method='POST' enctype='multipart/form-data'><input type='text' name='edit'></br>"
            output += "<input type='submit' value='Submit'></form>"
            output += "<a href='/restaurants'><h3>Back to Restaurants</h3></a>"

            self.wfile.write(output)

        elif self.path.endswith('/confirm-delete'):
            self.send_response(200)
            self.send_header('location', '/confirm-delete')
            self.send_header('content-type', 'text/html')
            self.end_headers()

            output = "<html><body>"
            output += "<h1>Are you sure you want to delete?</h1></br>"
            output += "<form method='POST' enctype='multipart/form-data'>"
            output += "<input type='submit' name='delete' value='Delete'>"
            output += "</form>"
            output += "</html></body>"

            self.wfile.write(output)

        else:

            self.send_error(404, 'File Not Found: %s' % self.path)

    def do_POST(self):
    	try:
            self.send_response(301)
            self.send_header('location', '/restaurants')
            self.end_headers()
            print self.headers
            ctype, pdict = cgi.parse_header(self.headers.getheader('content-type'))
            if ctype == 'multipart/form-data':
                fields = cgi.parse_multipart(self.rfile, pdict)
                print fields
                if 'edit' in fields.keys():
                    fullPath = os.path.split(self.path)[0]
                    rID = fullPath[1:]
                    newName = fields.get('edit')[0]
                    editRestaurant(rID, newName)
                elif 'restaurant' in fields.keys():
                    messagecontent = fields.get('restaurant')
                    createNewRestaurant(messagecontent[0])
                elif 'delete' in fields.keys():
                    print fields
            return

    	except:
            print('an error occured')


def main():
    try:
        port = 1234
        server = HTTPServer(('', port), WebServerHandler)
        print "Web Server running on port %s" % port
        server.serve_forever()
    except KeyboardInterrupt:
        print " ^C entered, stopping web server...."
        server.socket.close()

if __name__ == '__main__':
    main()
