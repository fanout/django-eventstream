from rest_framework.renderers import BrowsableAPIRenderer


class BrowsableAPIEventStreamRenderer(BrowsableAPIRenderer):
    """
    This renderer is used to render the browsable API for the EventStream.
    """

    # /!\ Do not change the format of the rendrer, it is used to determine the renderer in the view.
    # Ended if you really want to change the format, you have to change get_renderers method in the EventsViewSet.
    format = "api_sse"
    template = "django_eventstream/browsable-api-eventstream.html"

    def get_context(self, data, accepted_media_type, renderer_context):
        context = super().get_context(data, accepted_media_type, renderer_context)

        channels_error = "Here is no selected channels. Please check documentation to select channels."
        context["channels"] = data.get("channels", channels_error)
        if context["channels"] == "":
            context["channels"] = (
                "Here is no selected channels. Please check documentation to select channels or error."
            )

        messages_types_error = "Here is no selected messages types. Please check documentation to select messages types."
        context["messages_types"] = data.get("messages_types", messages_types_error)
        if context["messages_types"] == "":
            context["messages_types"] = (
                "Here is no selected channels. Please check documentation to select channels or error."
            )

        context["error"] = data.get("error")
        return context
