from channels.routing import ProtocolTypeRouter, URLRouter
import timeapp.routing

application = ProtocolTypeRouter({
    'http':
    URLRouter(timeapp.routing.urlpatterns),
})
