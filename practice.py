from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from database_setup import Base, Restaurant, MenuItem

# Connect to SQLite database
engine = create_engine('sqlite:///restaurantmenu.db')

# Connect the inherited Base class to your engine
Base.metadata.bind = engine

# DB Session class which is used to create sessions
DBSession = sessionmaker(bind=engine)

# Example session
session = DBSession()

# Now let's add items to our tables (which were already created)
# Tables = Restaurant & MenuItem

newEntry = Restaurant(name="Alec's first Restaurant")
session.add(newEntry)
session.commit()

menuEntry = MenuItem(name="Cheeseburger",
                     course="main",
                     description="The most amazing meal on the planet",
                     price="$8.99",
                     restaurant=newEntry)
session.add(menuItem)
session.commit()
