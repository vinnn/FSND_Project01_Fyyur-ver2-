# ----------------------------------------------------------------------------#
# Imports
# ----------------------------------------------------------------------------#
import json
import dateutil.parser
import babel
from flask import (
    Flask,
    render_template,
    request,
    Response,
    flash,
    redirect,
    url_for,
    abort
)
from flask_moment import Moment
from flask_sqlalchemy import SQLAlchemy
import logging
from logging import Formatter, FileHandler
from flask_wtf import Form
from forms import *
from flask_migrate import Migrate
from models import Venue, Artist, Show, db


# ----------------------------------------------------------------------------#
# App Config.
# ----------------------------------------------------------------------------#
app = Flask(__name__)

moment = Moment(app)
app.config.from_object('config')

# call init_app to initialise (reminder: SQLAlchemy db was
# not initialised in models.py)
db.init_app(app)
# instead of: db = SQLAlchemy(app)
# SQLAlchemy was called in models.py but not initialised


# connect to a local postgresql database
migrate = Migrate(app, db)


# ----------------------------------------------------------------------------#
# Filters.
# ----------------------------------------------------------------------------#
def format_datetime(value, format='medium'):
    date = dateutil.parser.parse(value)
    if format == 'full':
        format = "EEEE MMMM, d, y 'at' h:mma"
    elif format == 'medium':
        format = "EE MM, dd, y h:mma"
    return babel.dates.format_datetime(date, format, locale='en')


app.jinja_env.filters['datetime'] = format_datetime


# ----------------------------------------------------------------------------#
# Controllers.
# ----------------------------------------------------------------------------#
@app.route('/')
def index():
    return render_template('pages/home.html')


# Venues
# ----------------------------------------------------------------
@app.route('/venues')
def venues():
    # use venues data from database
    # num_shows should be aggregated based on
    # number of upcoming shows per venue
    places = Venue.query.distinct(Venue.city).distinct(Venue.state).all()
    data = []

    for place in places:
        dict_data = {}
        dict_data['city'] = place.city
        dict_data['state'] = place.state
        dict_data['venues'] = []

        venues_in_place = Venue.query.filter(
            Venue.city == place.city).filter(Venue.state == place.state).all()

        list_dict_venues = []
        for venue_in_place in venues_in_place:
            dict_venue = {}
            dict_venue['id'] = venue_in_place.id
            dict_venue['name'] = venue_in_place.name
            dict_venue['num_upcoming_shows'] = (
              Show.query.filter(Show.venue_id == venue_in_place.id)
                        .filter(Show.start_time > datetime.now())
                        .count()
                        )
            list_dict_venues.append(dict_venue)

        dict_data['venues'] = list_dict_venues

        data.append(dict_data)

    return render_template('pages/venues.html', areas=data)


@app.route('/venues/search', methods=['POST'])
def search_venues():
    # search on artists with partial string search,
    # case-insensitive.
    # seach for Hop should return "The Musical Hop".
    # search for "Music" should return "The Musical Hop" and
    # "Park Square Live Music & Coffee"

    # get the value of the 'name' in the form input element:
    search_term = request.form.get('search_term', '')
    found_venues = (Venue.query
                    .filter(Venue.name.ilike("%" + search_term + "%"))
                    .all()
                    )

    response = {}
    data_count = 0
    list_data = []
    for found_venue in found_venues:
        data_count += 1
        dict_data = {}

        dict_data["id"] = found_venue.id
        dict_data["name"] = found_venue.name
        num_upcoming = (
          Show.query.filter(Show.start_time > datetime.now())
                    .filter(Show.venue_id == found_venue.id).count()
          )

        dict_data["num_upcoming_shows"] = num_upcoming
        list_data.append(dict_data)

    response["count"] = data_count
    response["data"] = list_data

    return render_template(
      'pages/search_venues.html',
      results=response,
      search_term=request.form.get('search_term', '')
      )


@app.route('/venues/<int:venue_id>')
def show_venue(venue_id):
    # to show the venue page with the given venue_id
    # venue data from the venues table, using venue_id

    venue_selected = Venue.query.filter(Venue.id == venue_id).all()
    venue = venue_selected[0]

    dict_venue = {}
    dict_venue["id"] = venue.id
    dict_venue["name"] = venue.name
    dict_venue["genres"] = venue.genres
    dict_venue["address"] = venue.address
    dict_venue["city"] = venue.city
    dict_venue["state"] = venue.state
    dict_venue["phone"] = venue.phone
    dict_venue["website"] = venue.website_link
    dict_venue["facebook_link"] = venue.facebook_link
    dict_venue["seeking_talent"] = venue.seeking_talent
    dict_venue["seeking_description"] = venue.seeking_description
    dict_venue["image_link"] = venue.image_link

    dict_venue["past_shows"] = []
    dict_venue["upcoming_shows"] = []

    venue_shows = Show.query.filter(Show.venue_id == venue.id).all()
    for show in venue_shows:
        dict_show = {}
        dict_show["artist_id"] = show.artist_id
        artist = Artist.query.filter(Artist.id == show.artist_id).all()
        # query above returns a list of one element. Therefore extract
        # the element before accessing attributes:
        dict_show["artist_name"] = artist[0].name
        dict_show["artist_image_link"] = artist[0].image_link
        # date and time to be as a string as per filter function used later:
        dict_show["start_time"] = show.start_time.strftime("%d/%m/%Y, %H:%M")

        if show.start_time < datetime.now():
            dict_venue["past_shows"].append(dict_show)
        else:
            dict_venue["upcoming_shows"].append(dict_show)

    past_count_query = (
      db.session.query(Show).join(Venue)
      .filter(Show.venue_id == venue_id)
      .filter(Show.start_time < datetime.now())
      .all()
    )

    upcoming_count_query = (
      db.session.query(Show).join(Venue)
      .filter(Show.venue_id == venue_id)
      .filter(Show.start_time > datetime.now())
      .all()
    )

    dict_venue["past_shows_count"] = len(past_count_query)
    dict_venue["upcoming_shows_count"] = len(upcoming_count_query)

    # Alternative code:
    # past_count = (
    #   Show.query.filter(Show.venue_id == venue_id)
    #             .filter(Show.start_time < datetime.now())
    #             .distinct(Show.artist_id).count()
    #             )
    # dict_venue["past_shows_count"] = past_count
    #
    # upcoming_count = (
    #   Show.query.filter(Show.venue_id == venue_id)
    #             .filter(Show.start_time > datetime.now())
    #             .distinct(Show.artist_id).count()
    #             )
    # dict_venue["upcoming_shows_count"] = upcoming_count

    data = dict_venue

    return render_template('pages/show_venue.html', venue=data)


# Create Venue
# ----------------------------------------------------------------
@app.route('/venues/create', methods=['GET'])
def create_venue_form():
    form = VenueForm()
    return render_template('forms/new_venue.html', form=form)


@app.route('/venues/create', methods=['POST'])
def create_venue_submission():
    # form data as a new Venue record in the db

    form = VenueForm(request.form, meta={'csrf': False})
    if form.validate_on_submit():
        error = False
        try:
            venue = Venue(
              name=form.name.data,
              city=form.city.data,
              state=form.state.data,
              address=form.address.data,
              phone=form.phone.data,
              genres=form.genres.data,
              facebook_link=form.facebook_link.data,
              image_link=form.image_link.data,
              website_link=form.website_link.data,
              seeking_talent=form.seeking_talent.data,
              seeking_description=form.seeking_description.data
              )
            db.session.add(venue)
            db.session.commit()

        # on successful db insert, flash success
            flash('Venue ' + request.form['name'] +
                  ' was successfully listed!')

        except():
            db.session.rollback()
            error = True
            print(sys.exc_info())
    # on unsuccessful db insert, an error is flashed
    # e.g., flash('An error occurred. Venue '
    # + data.name + ' could not be listed.')
    # see: http://flask.pocoo.org/docs/1.0/patterns/flashing/
            flash('An error occurred. Venue '
                  + request.form['name']
                  + ' could not be listed.')

        finally:
            db.session.close()

        if error:
            abort(400)

    # on successful db insert, flash success
    else:
        flash('An error occurred. The creation input for Venue '
              + request.form['name'] + ' were not all valid.')

    return render_template('pages/home.html')


@app.route('/venues/<venue_id>', methods=['DELETE'])
def delete_venue(venue_id):
    # Endpoint taking a venue_id, and using
    # SQLAlchemy ORM to delete a record.

    venue_to_delete = Venue.query.get(venue_id)
    try:
        error = False
        db.session.delete(venue_to_delete)
        db.session.commit()
    except():
        db.session.rollback()
        error = True
        print(sys.exc_info())
    finally:
        db.session.close()
    if error:
        abort(400)

    # BONUS CHALLENGE: Implement a button to delete a Venue on a
    # Venue Page, have it so that clicking that button delete it
    # from the db then redirect the user to the homepage
    return None


# Artists
# ----------------------------------------------------------------
@app.route('/artists')
def artists():
    # artist data returned from querying the database
    artists = Artist.query.all()

    data = []
    for artist in artists:
        data_dict = {}
        data_dict["id"] = artist.id
        data_dict["name"] = artist.name
        data.append(data_dict)

    return render_template('pages/artists.html', artists=data)


@app.route('/artists/search', methods=['POST'])
def search_artists():
    # search on artists with partial string search,
    # case-insensitive.
    # # seach for "A" should return "Guns N Petals",
    # "Matt Quevado", and "The Wild Sax Band".
    # search for "band" should return "The Wild Sax Band".

    # get the value of the 'name' in the form input element:
    search_term = request.form.get('search_term', '')
    print("search_term *******************")
    print(search_term)
    found_artists = (
      Artist.query.filter(Artist.name.ilike("%" + search_term + "%")).all()
      )

    response = {}
    data_count = 0
    data_list = []
    for found_artist in found_artists:
        data_count += 1
        data_dict = {}

        data_dict["id"] = found_artist.id
        data_dict["name"] = found_artist.name

        num_upcoming_query = (
          db.session.query(Show).join(Artist)
          .filter(Show.start_time > datetime.now())
          .all()
        )
        data_dict["num_upcoming_shows"] = len(num_upcoming_query)

        # Alternative code:
        # num_upcoming = (
        #   Show.query.filter(Show.start_time > datetime.now())
        #             .filter(Show.artist_id == found_artist.id).count()
        #   )
        # data_dict["num_upcoming_shows"] = num_upcoming

        data_list.append(data_dict)

    response["count"] = data_count
    response["data"] = data_list

    return render_template(
      'pages/search_artists.html',
      results=response,
      search_term=request.form.get('search_term', '')
      )


@app.route('/artists/<int:artist_id>')
def show_artist(artist_id):
    # shows the artist page with the given artist_id

    artist_selected = Artist.query.filter(Artist.id == artist_id).all()
    artist = artist_selected[0]

    dict_data = {}
    dict_data["id"] = artist.id
    dict_data["name"] = artist.name
    dict_data["genres"] = artist.genres
    dict_data["city"] = artist.city
    dict_data["state"] = artist.state
    dict_data["phone"] = artist.phone
    dict_data["website"] = artist.website_link
    dict_data["facebook_link"] = artist.facebook_link
    dict_data["seeking_venue"] = artist.seeking_venue
    dict_data["seeking_description"] = artist.seeking_description
    dict_data["image_link"] = artist.image_link

    dict_data["past_shows"] = []
    dict_data["upcoming_shows"] = []

    artist_shows = Show.query.filter(Show.artist_id == artist.id).all()
    for show in artist_shows:
        dict_show = {}
        dict_show["venue_id"] = show.venue_id
        venue = Venue.query.filter(Venue.id == show.venue_id).all()
        # query above returns a list of one element. Therefore extract
        # the element before accessing attributes:
        dict_show["venue_name"] = venue[0].name
        dict_show["venue_image_link"] = venue[0].image_link
        # date and time to be as a string as per filter function used later:
        dict_show["start_time"] = show.start_time.strftime("%d/%m/%Y, %H:%M")

        if show.start_time < datetime.now():
            dict_data["past_shows"].append(dict_show)
        else:
            dict_data["upcoming_shows"].append(dict_show)

    past_count_query = (
      db.session.query(Show).join(Artist)
      .filter(Show.artist_id == artist_id)
      .filter(Show.start_time < datetime.now())
      .all()
    )

    upcoming_count_query = (
      db.session.query(Show).join(Artist)
      .filter(Show.artist_id == artist_id)
      .filter(Show.start_time > datetime.now())
      .all()
    )

    dict_data["past_shows_count"] = len(past_count_query)
    dict_data["upcoming_shows_count"] = len(upcoming_count_query)

    # alternative code:
    # past_count = (
    #   Show.query.filter(Show.artist_id == artist_id)
    #             .filter(Show.start_time < datetime.now())
    #             .distinct(Show.venue_id).count()
    #   )

    # upcoming_count = (
    #   Show.query.filter(Show.artist_id == artist_id)
    #             .filter(Show.start_time > datetime.now())
    #             .distinct(Show.venue_id).count()
    #   )

    # dict_data["past_shows_count"] = past_count
    # dict_data["upcoming_shows_count"] = upcoming_count

    data = dict_data

    return render_template('pages/show_artist.html', artist=data)


# Update
# ----------------------------------------------------------------
@app.route('/artists/<int:artist_id>/edit', methods=['GET'])
def edit_artist(artist_id):
    # fields of form populated with data from artist with ID <artist_id>

    artist = Artist.query.filter_by(id=artist_id).first_or_404()
    form = ArtistForm(obj=artist)

    return render_template('forms/edit_artist.html', form=form, artist=artist)


@app.route('/artists/<int:artist_id>/edit', methods=['POST'])
def edit_artist_submission(artist_id):
    # takes values from the form submitted, and update existing
    # artist record with ID <artist_id> using the new attributes

    artist = Artist.query.filter_by(id=artist_id).first_or_404()
    form = ArtistForm(request.form, meta={'csrf': False})

    if form.validate_on_submit():
        error = False
        try:
            artist.name = form.name.data
            artist.city = form.city.data
            artist.state = form.state.data
            artist.phone = form.phone.data
            artist.genres = form.genres.data
            artist.facebook_link = form.facebook_link.data
            artist.image_link = form.image_link.data
            artist.website_link = form.website_link.data
            artist.seeking_venue = form.seeking_venue.data
            artist.seeking_description = form.seeking_description.data
            db.session.commit()
            flash('Artist ' + artist.name + ' was successfully edited!')

        except():
            db.session.rollback()
            error = True
            print(sys.exc_info())

        finally:
            db.session.close()

        if error:
            abort(400)

    return redirect(url_for('show_artist', artist_id=artist_id))


@app.route('/venues/<int:venue_id>/edit', methods=['GET'])
def edit_venue(venue_id):
    # fields of form populated with values from venue with ID <venue_id>

    venue = Venue.query.filter_by(id=venue_id).first_or_404()
    form = VenueForm(obj=venue)

    return render_template('forms/edit_venue.html', form=form, venue=venue)


@app.route('/venues/<int:venue_id>/edit', methods=['POST'])
def edit_venue_submission(venue_id):
    # takes values from the form submitted, and update existing
    # venue record with ID <venue_id> using the new attributes

    venue = Venue.query.filter_by(id=venue_id).first_or_404()
    form = VenueForm(request.form, meta={'csrf': False})

    if form.validate_on_submit():
        error = False
        try:
            venue.name = form.name.data
            venue.city = form.city.data
            venue.state = form.state.data
            venue.address = form.address.data
            venue.phone = form.phone.data
            venue.genres = form.genres.data
            venue.facebook_link = form.facebook_link.data
            venue.image_link = form.image_link.data
            venue.website_link = form.website_link.data
            venue.seeking_talent = form.seeking_talent.data
            venue.seeking_description = form.seeking_description.data
            db.session.commit()
            flash('Venue ' + venue.name + ' was successfully edited!')

        except():
            db.session.rollback()
            error = True
            print(sys.exc_info())

        finally:
            db.session.close()

        if error:
            abort(400)

    return redirect(url_for('show_venue', venue_id=venue_id))


# Create Artist
# ----------------------------------------------------------------
@app.route('/artists/create', methods=['GET'])
def create_artist_form():
    form = ArtistForm()
    return render_template('forms/new_artist.html', form=form)


@app.route('/artists/create', methods=['POST'])
def create_artist_submission():
    # called upon submitting the new artist listing form
    # form data inserted as a new Venue record in the db

    form = ArtistForm(request.form, meta={'csrf': False})
    if form.validate_on_submit():
        error = False
        try:
            artist = Artist(
              name=form.name.data,
              city=form.city.data,
              state=form.state.data,
              phone=form.phone.data,
              genres=form.genres.data,
              facebook_link=form.facebook_link.data,
              image_link=form.image_link.data,
              website_link=form.website_link.data,
              seeking_venue=form.seeking_venue.data,
              seeking_description=form.seeking_description.data)
            print("in try")
            db.session.add(artist)
            db.session.commit()

    # on successful db insert, flash success
            flash('Artist ' + request.form['name']
                  + ' was successfully listed!')

        except():
            print("in except")
            db.session.rollback()
            error = True
            print(sys.exc_info())
    # on unsuccessful db insert, error is flashed
            flash('An error occurred. Artist '
                  + request.form['name']
                  + ' could not be listed.')

        finally:
            db.session.close()

        if error:
            abort(400)

    # on successful db insert, flash success
    else:
        flash('An error occurred. The creation input for Artist '
              + request.form['name'] + ' were not all valid.')

    return render_template('pages/home.html')


# Shows
# ----------------------------------------------------------------
@app.route('/shows')
def shows():
    # displays list of shows at /shows
    # venues data ffrom database.
    # num_shows should be aggregated based
    # on number of upcoming shows per venue.

    shows = Show.query.all()

    data_list = []
    for show in shows:
        data_dict = {}
        data_dict["venue_id"] = show.venue_id
        data_dict["venue_name"] = (
          Venue.query.filter(Venue.id == show.venue_id)[0].name
          )
        data_dict["artist_id"] = show.artist_id
        data_dict["artist_name"] = (
          Artist.query.filter(Artist.id == show.artist_id)[0].name
          )
        data_dict["artist_image_link"] = (
          Artist.query.filter(Artist.id == show.artist_id)[0].image_link
          )
        data_dict["start_time"] = (
          show.start_time.strftime("%d/%m/%Y, %H:%M")
          )
        data_list.append(data_dict)

    return render_template('pages/shows.html', shows=data_list)


@app.route('/shows/create')
def create_shows():
    # renders form. do not touch.
    form = ShowForm()
    return render_template('forms/new_show.html', form=form)


@app.route('/shows/create', methods=['POST'])
def create_show_submission():
    # called to create new shows in the db, upon
    # submitting new show listing form

    form = ShowForm(request.form, meta={'csrf': False})
    if form.validate_on_submit():
        error = False
        try:
            show = Show(
              venue_id=form.venue_id.data,
              artist_id=form.artist_id.data,
              start_time=form.start_time.data)
            db.session.add(show)
            db.session.commit()

    # on successful db insert, flash success
            flash('Show was successfully listed!')

        except():
            db.session.rollback()
            error = True
            print(sys.exc_info())
    # on unsuccessful db insert, error is flashed
            flash('An error occurred. Show could not be listed.')

        finally:
            db.session.close()

        if error:
            abort(400)

    # on successful db insert, flash success
    else:
        flash('An error occurred. The creation inputs were not all valid.')

    return render_template('pages/home.html')


@app.errorhandler(400)
def bad_request_error(error):
    return render_template('errors/400.html'), 404


@app.errorhandler(401)
def unauthorized_error(error):
    return render_template('errors/401.html'), 401


@app.errorhandler(404)
def not_found_error(error):
    return render_template('errors/404.html'), 404


@app.errorhandler(500)
def server_error(error):
    return render_template('errors/500.html'), 500


if not app.debug:
    file_handler = FileHandler('error.log')
    file_handler.setFormatter(
        Formatter(
          '%(asctime)s %(levelname)s: %(message)s [in %(pathname)s:%(lineno)d]'
          )
    )
    app.logger.setLevel(logging.INFO)
    file_handler.setLevel(logging.INFO)
    app.logger.addHandler(file_handler)
    app.logger.info('errors')


# ----------------------------------------------------------------------------#
# Launch.
# ----------------------------------------------------------------------------#
# Default port:
if __name__ == '__main__':
    app.run()

# Or specify port manually:
'''
if __name__ == '__main__':
    port = int(os.environ.get('PORT', 5000))
    app.run(host='0.0.0.0', port=port)
'''
