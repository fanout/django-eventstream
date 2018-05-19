from channels.routing import ProtocolTypeRouter, URLRouter
import basic.routing

application = ProtocolTypeRouter({
    'http': URLRouter(basic.routing.urlpatterns),
})
