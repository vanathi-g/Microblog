from flask import g, render_template, flash, redirect, url_for, request, jsonify, current_app
from flask_login import login_required, current_user

from app import db
from app.main.forms import EditProfileForm, PostForm, SearchForm
from app.models import User, Post

from werkzeug.urls import url_parse

from datetime import datetime

from app.main import bp

@bp.before_request
def before_request():
	if current_user.is_authenticated:
		current_user.last_seen = datetime.utcnow()
		db.session.commit()
		g.search_form = SearchForm()


# HOME PAGE 
@bp.route('/', methods=['GET', 'POST'])
@bp.route('/index', methods=['GET', 'POST'])
@login_required
def index():
	form = PostForm()
	if form.validate_on_submit():
		post = Post(body=form.post.data, author=current_user)
		flash('Your post is live now!', 'success')
		db.session.add(post)
		db.session.commit()
		return redirect(url_for('main.index'))
	page = request.args.get('page', 1, type = int)
	posts = current_user.followed_posts().paginate(
		page, current_app.config['POSTS_PER_PAGE'], False)
	next_url = url_for('main.index', page=posts.next_num) \
		if posts.has_next else None
	prev_url = url_for('main.index', page=posts.prev_num) \
		if posts.has_prev else None
	return render_template("index.html", title='Home Page', form=form,
						   posts=posts.items, next_url=next_url, prev_url=prev_url)

# TO VIEW USER'S PROFILE
@bp.route('/user/<username>')
@login_required
def user(username):
	user = User.query.filter_by(username=username).first_or_404()
	page = request.args.get('page', 1, type=int)
	posts = user.posts.order_by(Post.timestamp.desc()).paginate(
		page, current_app.config['POSTS_PER_PAGE'], False)
	next_url = url_for('main.user', username=user.username, page=posts.next_num) \
		if posts.has_next else None
	prev_url = url_for('main.user', username=user.username, page=posts.prev_num) \
		if posts.has_prev else None
	return render_template('user.html', user=user, posts=posts.items,
						   next_url=next_url, prev_url=prev_url)

# TO EDIT USER PROFILE
@bp.route('/edit_profile', methods=['GET', 'POST'])
@login_required
def edit_profile():
	form = EditProfileForm(current_user.username)
	if form.validate_on_submit():
		current_user.username = form.username.data
		current_user.first_name = form.firstname.data
		current_user.last_name = form.lastname.data
		current_user.about_me = form.about_me.data
		db.session.commit()
		flash("Changes have been saved!", 'success')
		return redirect(url_for('main.user', username = current_user.username))
	elif request.method == 'GET':
		form.firstname.data = current_user.first_name
		form.lastname.data = current_user.last_name
		form.username.data = current_user.username
		form.about_me.data = current_user.about_me
	return render_template('edit_profile.html', title='Edit Profile', form=form)

# TO FOLLOW USER
@bp.route('/follow/<username>')
@login_required
def follow(username):
	user = User.query.filter_by(username=username).first()
	if user is None:
		flash('User {} not found.'.format(username), 'warning')
		return redirect(url_for('main.index'))
	if user == current_user:
		flash('You cannot follow yourself!', 'warning')
		return redirect(url_for('main.user', username=username))
	current_user.follow(user)
	db.session.commit()
	flash('You are following {}!'.format(username), 'success')
	return redirect(url_for('main.user', username=username))

# TO UNFOLLOW USER
@bp.route('/unfollow/<username>')
@login_required
def unfollow(username):
	user = User.query.filter_by(username=username).first()
	if user is None:
		flash('User {} not found.'.format(username), 'warning')
		return redirect(url_for('main.index'))
	if user == current_user:
		flash('You cannot unfollow yourself!', 'warning')
		return redirect(url_for('main.user', username=username))
	current_user.unfollow(user)
	db.session.commit()
	flash('You are not following {}.'.format(username), 'warning')
	return redirect(url_for('main.user', username=username))

# FOR EXPLORE PAGE
@bp.route('/explore')
@login_required
def explore():
	page = request.args.get('page', 1, type=int)
	posts = Post.query.order_by(Post.timestamp.desc()).paginate(
		page, current_app.config['POSTS_PER_PAGE'], False)
	next_url = url_for('main.explore', page=posts.next_num) \
		if posts.has_next else None
	prev_url = url_for('main.explore', page=posts.prev_num) \
		if posts.has_prev else None
	return render_template("index.html", title='Explore', posts=posts.items,
						  next_url=next_url, prev_url=prev_url)

# FOR SEARCHING FUNCTIONALITY
@bp.route('/search')
@login_required
def search():
    if not g.search_form.validate():
        return redirect(url_for('main.explore'))
    page = request.args.get('page', 1, type=int)
    posts, total = Post.search(g.search_form.q.data, page,
                               current_app.config['POSTS_PER_PAGE'])
    next_url = url_for('main.search', q=g.search_form.q.data, page=page + 1) \
        if total > page * current_app.config['POSTS_PER_PAGE'] else None
    prev_url = url_for('main.search', q=g.search_form.q.data, page=page - 1) \
        if page > 1 else None
    return render_template('search.html', title='Search', posts=posts,
                           next_url=next_url, prev_url=prev_url)