from bot.handlers import admin, my_ads, post_ad, search, start

all_routers = (
    start.router,
    post_ad.router,
    my_ads.router,
    search.router,
    admin.router,
)
