from flask import render_template, redirect, url_for, request, flash, make_response
from flask_login import login_required, current_user
from flask.globals import current_app
from . import main
from .forms import EditProfileForm, EditProfileAdminForm, PostForm, PostReplyForm, CommentForm
from .. import db
from ..models import Permission, User, Role, Post, Reply, Comment
from ..decorators import admin_required, permission_required
from werkzeug.utils import secure_filename

@main.route('/')
def index():
    page = request.args.get('page', 1, type=int)
    pagination = Post.query.order_by(Post.timestamp.desc()).paginate(page, per_page=current_app.config['DARKWEB_POSTS_PER_PAGE'],error_out=False)
    posts = pagination.items
    return render_template('index.html', posts=posts, pagination=pagination)

#---- 회원 프로필 ----
@main.route('/user/<username>')
def user(username):
    user = User.query.filter_by(username=username).first_or_404()  
    page = request.args.get('page', 1, type=int)
    pagination = user.posts.order_by(Post.timestamp.desc()).paginate(page, per_page=current_app.config['DARKWEB_POSTS_PER_PAGE'],error_out=False)
    posts = pagination.items
    return render_template('user.html', user=user, posts=posts, pagination=pagination)

# 회원 프로필 수정
# 회원은 자신의 프로필 수정할 수 있음
@main.route('/edit-profile', methods=['GET', 'POST'])
@login_required
def edit_profile():
    form = EditProfileForm()
    if form.validate_on_submit():
        current_user.name = form.name.data
        current_user.location = form.location.data
        current_user.about_me = form.about_me.data
        db.session.add(current_user._get_current_object())
        db.session.commit()
        flash('프로필을 수정하였습니다.')
        return redirect(url_for('.user', username=current_user.username))

    form.name.data = current_user.name
    form.location.data = current_user.location
    form.about_me.data = current_user.about_me
    return render_template('edit_profile.html', form=form)

# 관리자 프로필 수정
# 관리자는 자신뿐 아니라 회원들의 프로필 수정할 수 있음
@main.route('/edit-profile/<int:id>', methods=['GET', 'POST'])
@login_required
@admin_required
def edit_profile_admin(id):
    user = User.query.get_or_404(id)
    form = EditProfileAdminForm(user=user)
    if form.validate_on_submit():
        user.email = form.email.data
        user.username = form.username.data
        user.role = Role.query.get(form.role.data)
        user.name = form.name.data
        user.location = form.location.data
        user.about_me = form.about_me.data
        db.session.add(user)
        db.session.commit()
        flash('프로필을 수정하였습니다.')
        return redirect(url_for('.user', username=user.username))

    form.email.data = user.email
    form.username.data = user.username
    form.role.data = user.role_id
    form.name.data = user.name
    form.location.data = user.location
    form.about_me.data = user.about_me
    return render_template('edit_profile_admin.html', form=form, user=user)

# 글쓰기
@main.route('/post_write', methods=['GET', 'POST'])
@login_required
def post_write():
    form = PostForm()
    if form.validate_on_submit():
        filename = form.upload.data.filename
        post = Post(subject=form.subject.data,
                    body=form.body.data,
                    author=current_user._get_current_object(),
                    filepath=secure_filename(filename))
        if request.method == 'POST':
            f = request.files['upload']
            f.save('./uploads/'+ current_user._get_current_object().email + '/' + secure_filename(f.filename))
        db.session.add(post)
        db.session.commit()
        return redirect(url_for('main.index'))
    return render_template('post_write.html', form=form)

# 댓글쓰기
@main.route('/post_reply/<int:post_id>', methods=['GET', 'POST'])
def post_reply(post_id):
    form = PostReplyForm()
    post = Post.query.get_or_404(post_id)
    if form.validate_on_submit():
        reply = Reply(body=request.form["body"], author=current_user._get_current_object())
        post.replies.append(reply)
        db.session.commit()
        return redirect('{}#reply_{}'.format(url_for('main.post_reply', post_id=post_id), reply.id))
    return render_template('post_reply.html', post=post, form=form)

#-- 추천 ----
@main.route('/recommend_post/<int:post_id>', methods=['GET', 'POST'])
@login_required
def recommend_post(post_id):
    post = Post.query.get_or_404(post_id)
    if current_user._get_current_object() == post.author:
        flash('본인이 작성한 글은 추천할수 없습니다')
    else:
        post.like.append(current_user._get_current_object())
        db.session.commit()
    return redirect(url_for('main.post_reply', post_id=post_id))

@main.route('/recommend_reply/<int:reply_id>', methods=['GET', 'POST'])
@login_required
def recommend_reply(reply_id):
    reply = Reply.query.get_or_404(reply_id)
    if current_user._get_current_object() == reply.author:
        flash('본인이 작성한 글은 추천할수 없습니다')
    else:
        reply.like.append(current_user._get_current_object())
        db.session.commit()
    return redirect(url_for('main.post_reply', post_id=reply.post_id))

# ---- post comment -----
@main.route('/write_post_comment/<int:post_id>', methods=['GET', 'POST'])
@login_required
def write_post_comment(post_id):
    form = CommentForm()
    post = Post.query.get_or_404(post_id)
    if form.validate_on_submit():
        comment = Comment(body=form.body.data, author=current_user._get_current_object())
        post.comments.append(comment)
        db.session.commit()
        #return redirect(url_for('question.detail', question_id=question_id))
        return redirect('{}#comment_{}'.format(
            url_for('main.post_reply', post_id=post_id), comment.id))

    return render_template('comment_write.html', form=form)

@main.route('/modify_post_comment/<int:comment_id>', methods=['GET', 'POST'])
@login_required
def modify_post_comment(comment_id):
    comment = Comment.query.get_or_404(comment_id)
    if current_user._get_current_object() != comment.author:
        flash('수정권한이 없습니다')
        return redirect(url_for('main.post_reply', post_id=comment.post.id))

    if request.method == 'POST':
        form = CommentForm()
        if form.validate_on_submit():
            form.populate_obj(comment)
            db.session.commit()
            #return redirect(url_for('question.detail', question_id=comment.question.id))
            return redirect('{}#comment_{}'.format(
                url_for('main.post_reply', post_id=comment.post.id), comment.id))
    else:
        form = CommentForm(obj=comment)

    return render_template('comment_write.html', form=form)

@main.route('/delete_post_comment/<int:comment_id>')
@login_required
def delete_post_comment(comment_id):
    comment = Comment.query.get_or_404(comment_id)
    post_id = comment.post.id
    if current_user._get_current_object() != comment.author:
        flash('삭제권한이 없습니다')
        return redirect(url_for('main.post_reply', post_id=post_id))

    db.session.delete(comment)
    db.session.commit()
    return redirect(url_for('main.post_reply', post_id=post_id))

# ---- reply comment ----
@main.route('/write_reply_comment/<int:reply_id>', methods=['GET', 'POST'])
@login_required
def write_reply_comment(reply_id):
    form = CommentForm()
    reply = Reply.query.get_or_404(reply_id)
    if form.validate_on_submit():
        comment = Comment(body=form.body.data, author=current_user._get_current_object())
        reply.comments.append(comment)
        db.session.commit()
        #return redirect(url_for('question.detail', question_id=question_id))
        return redirect('{}#comment_{}'.format(
            url_for('main.post_reply', post_id=reply.post.id), comment.id))

    return render_template('comment_write.html', form=form)

@main.route('/modify_reply_comment/<int:comment_id>', methods=['GET', 'POST'])
@login_required
def modify_reply_comment(comment_id):
    comment = Comment.query.get_or_404(comment_id)
    if current_user._get_current_object() != comment.author:
        flash('수정권한이 없습니다')
        return redirect(url_for('main.post_reply', post_id=comment.post.id))

    if request.method == 'POST':
        form = CommentForm()
        if form.validate_on_submit():
            form.populate_obj(comment)
            db.session.commit()
            #return redirect(url_for('question.detail', question_id=comment.question.id))
            return redirect('{}#comment_{}'.format(
                url_for('main.post_reply', post_id=comment.post.id), comment.id))
    else:
        form = CommentForm(obj=comment)

    return render_template('comment_write.html', form=form)

@main.route('/delete_reply_comment/<int:comment_id>')
@login_required
def delete_reply_comment(comment_id):
    comment = Comment.query.get_or_404(comment_id)
    post_id = comment.post.id
    if current_user._get_current_object() != comment.author:
        flash('삭제권한이 없습니다')
        return redirect(url_for('main.post_reply', post_id=post_id))

    db.session.delete(comment)
    db.session.commit()
    return redirect(url_for('main.post_reply', post_id=post_id))

#---- cleaning ----
@main.route('/cleaning')
@login_required
@permission_required(Permission.CLEAN)
def cleaning():
    page = request.args.get('page', 1, type=int)
    pagination = Comment.query.order_by(Comment.timestamp.desc()).paginate(
        page, per_page=current_app.config['DARKWEB_COMMENTS_PER_PAGE'],error_out=False)
    comments = pagination.items
    return render_template('cleaning.html', comments=comments,
                pagination=pagination, page=page)

@main.route('/cleaning/enable/<int:id>')
@login_required
@permission_required(Permission.CLEAN)
def cleaning_enable(id):
    comment = Comment.query.get_or_404(id)
    comment.disabled = False
    db.session.add(comment)
    db.session.commit()
    return redirect(url_for('.cleaning',
                            page=request.args.get('page', 1, type=int)))


@main.route('/cleaning/disable/<int:id>')
@login_required
@permission_required(Permission.CLEAN)
def cleaning_disable(id):
    comment = Comment.query.get_or_404(id)
    comment.disabled = True
    db.session.add(comment)
    db.session.commit()
    return redirect(url_for('.cleaning',
                            page=request.args.get('page', 1, type=int)))

#다운로드 HTML 렌더링
@main.route('/download')
@login_required
@permission_required(Permission.FILE)
def down_page():
	files = os.listdir("../../uploads")
	return render_template('filedown.html',files=files)

#파일 다운로드 처리
@main.route('/fileDownload', methods = ['GET', 'POST'])
@login_required
@permission_required(Permission.FILE)
def down_file():
	if request.method == 'POST':
		sw=0
		files = os.listdir("../../uploads")
		for x in files:
			if(x==request.form['file']):
				sw=1

		path = "../../uploads/" 
		return send_file(path + request.form['file'], attachment_filename = request.form['file'], as_attachment=True)