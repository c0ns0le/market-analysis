def includeme(config):
    # config.add_static_view('static', 'static', cache_max_age=3600)
    config.add_route('portfolio', '/')
    config.add_route('home_test', '/test')
    config.add_route('single_stock_info_test', '/single_stock_info_test')
    config.add_route('graph_demo', '/graph_demo')
    config.add_route('login', '/login')
    config.add_route('logout', '/logout')
    config.add_route('search', '/search')
    config.add_route('userinfo', '/userinfo')
    config.add_route('admin', '/admin')
