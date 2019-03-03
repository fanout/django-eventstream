from channels.routing import ProtocolTypeRouter, URLRouter
import chat.routing

application = ProtocolTypeRouter({
	'http': URLRouter(chat.routing.urlpatterns),
})
