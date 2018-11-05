###############################
####### SETUP (OVERALL) #######
###############################

## Import statements
# Import statements
import os
import sys
import flask
from flask import Flask, render_template, session, redirect, url_for, flash, request, redirect
from flask_wtf import FlaskForm
from wtforms import StringField, SubmitField, ValidationError, IntegerField # Note that you may need to import more here! Check out examples that do what you want to figure out what.
from wtforms.validators import Required, Length # Here, too
from flask_sqlalchemy import SQLAlchemy
from sqlalchemy import UniqueConstraint
from flask_script import Manager, Shell
from geopy.geocoders import Nominatim
import json
import requests
## App setup code
#basedir = os.path.abspath(os.path.dirname(__file__))


app = Flask(__name__)
app.debug = True

## All app.config values
## Statements for db setup (and manager setup if using Manager)
app.config['SECRET_KEY'] = 'hard to guess string from si364'
app.config["SQLALCHEMY_DATABASE_URI"] = "postgresql://localhost/midterm_fixed_db"
app.config['SQLALCHEMY_COMMIT_ON_TEARDOWN'] = True
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

db = SQLAlchemy(app)



######################################
######## HELPER FXNS (If any) ########
######################################




##################
##### MODELS #####
##################

class User(db.Model):
    __tablename__ = "User"
    id = db.Column(db.Integer,primary_key=True)
    username = db.Column(db.String(64))

    def __repr__(self):
        return "Username: {} (ID: {})".format(self.username, self.id)


class Post(db.Model):
    __tablename__ = "Post"
    id = db.Column(db.Integer,primary_key=True)
    post_text = db.Column(db.String(1000))
    username = db.Column(db.String(1000))
    user_id = db.Column(db.ForeignKey("User.id"))
    city = db.Column(db.String(1000))
    weather = db.Column(db.String(1000))
    __table_args__ = (UniqueConstraint('username', 'post_text', 'city', name='post_constraint'),)

    def __repr__(self):
        return "User ID: {}, Username: {}, Text: {}, City: {} (Post ID: {})".format(self.user_id, self.username, self.post_text, self.city, self.id)

class Share(db.Model):
    __tablename__ = "Share"
    id = db.Column(db.Integer,primary_key=True)
    share_from = db.Column(db.String(1000))
    share_to = db.Column(db.String(1000))
    post_id = db.Column(db.ForeignKey("Post.id"))
    __table_args__ = (UniqueConstraint('share_from', 'share_to', 'post_id', name='share_constraint'),)

    def __repr__(self):
        return "From: {}, To: {} (Post ID: {})".format(self.share_from, self.share_to, self.post_id)


###################
###### FORMS ######
###################

class PostForm(FlaskForm):
    def validate_length(self, field):
        text = str(field)
        if len(text) > 1000:
            raise ValidationError("Post text must be under 1000 characters!")

    #name = StringField("Please enter your name: ",validators=[Required()])
    username = StringField("Please enter your username: ",validators=[Required()])
    text = StringField("Write your post here (1000 character max): ",validators=[Required()])
    city = StringField("Enter your city to add the daily weather in your city to your post: ")
    submit = SubmitField()

class ShareForm(FlaskForm):
    username_from = StringField("Who is this share from? (username): ",validators=[Required()])
    username_to = StringField("Who is this share to? (username): ",validators=[Required()])
    post_id = StringField("Which post would you like to share? (post_id): ",validators=[Required()])
    submit = SubmitField()



#######################
###### VIEW FXNS ######
#######################

@app.route('/')
def home():
    return render_template('base.html')

#form = PostForm()

@app.route('/make_post', methods = ['POST', 'GET'])
def make_post():

    context = {}
    form = PostForm()

    if request.method == "POST":
        post = Post()
        #form = PostForm()

        #print(form.name.data, file=sys.stderr)
        post.username = form.username.data
        post.post_text = form.text.data
        post.city = form.city.data

        geolocator = Nominatim(user_agent="test")
        location = geolocator.geocode(post.city)
        url = "https://api.darksky.net/forecast/c7f71279af92395e316a9c2760491416/" + str(location.latitude) + "," + str(location.longitude)
        response = requests.get(url)
        jData = json.loads(response.content)
        report = "The weather in " + post.city + " today was " + jData['hourly']['summary'] + " with a high of " + str(jData['daily']['data'][0]['temperatureHigh']) + " and a low of " + str(jData['daily']['data'][0]['temperatureLow'])
        post.weather = report
        print("weather: " + post.weather)
        db.session.add(post)
        #print(str(post), file=sys.stderr)
        try:
            db.session.commit()
        except:
            context["error"] = "Exact post by user already exists"
            db.session.rollback()

        #add user
        user = User()
        user.username = post.username
        db.session.add(user)
        db.session.commit()

        return render_template('base.html', **context)
        #return flask.redirect(flask.url_for('home'))


    return render_template('make_post.html', form=form)

@app.route('/post_feed', methods = ['GET', 'POST'])
def post_feed():
    all_posts = Post.query.all()
    context = {}
    context["posts"] = all_posts

    print(context)
    return render_template('post_feed.html', **context)

@app.route('/make_share', methods = ['POST', 'GET'])
def make_share():
    form = ShareForm()
    context = {}

    if request.method == "POST":
        share = Share()
        share.share_from = form.username_from.data
        share.share_to = form.username_to.data
        share.post_id = form.post_id.data
        print(share)
        db.session.add(share)
        try:
            db.session.commit()
        except:
            context["error"] = "Error creating the share.  Share exists, or user/post does not exist"
            db.session.rollback()
        
        return render_template('base.html', **context)            
        #return flask.redirect(flask.url_for('home'), **context)

    return render_template('make_share.html', form=form)

@app.route('/share_feed', methods = ['GET', 'POST'])
def share_feed():
    context = {}
    shares = Share.query.all()
    all_posts = []
    for share in shares: 
        post = Post.query.filter_by(id=share.post_id).first() 
        post.shared_by = share.share_from
        post.shared_to = share.share_to
        all_posts.append(post)
    
    context["posts"] = all_posts 
    print(context)

    return render_template('share_feed.html', **context)

@app.route('/user_page/<user>/', methods = ['GET', 'POST'])
def user_page(user):
    context = {}
    context["user"] = user
    all_posts = Post.query.filter_by(username=user).all()
    context["posts"] = all_posts
    return render_template('user_page.html', **context)


## Error handling
@app.errorhandler(404)
def page_not_found(e):
    return render_template('404.html'), 404

## Code to run the application...

if __name__ == '__main__':
    db.create_all() # Will create any defined models when you run the application
    app.run(use_reloader=True,debug=True) # The usual

# Put the code to do so here!
# NOTE: Make sure you include the code you need to initialize the database structure when you run the application!
