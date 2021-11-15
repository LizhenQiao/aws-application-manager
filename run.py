from app import webapp
webapp.secret_key = "you-will-never-know-lol"
webapp.jinja_env.auto_reload = True
webapp.config['TEMPLATES_AUTO_RELOAD'] = True
webapp.config['SESSION_TYPE'] = 'filesystem'

webapp.run('0.0.0.0', 5000, debug=False)
