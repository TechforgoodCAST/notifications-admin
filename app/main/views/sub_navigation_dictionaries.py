def features_nav():
    return [
        {
            "name": "Features",
            "link": "main.features",
            "sub_navigation_items": [
                {
                    "name": "Text messages",
                    "link": "main.features_sms",
                }
            ]
        },
        {
            "name": "Roadmap",
            "link": "main.roadmap",
        },
        {
            "name": "Who can use Notify",
            "link": "main.who_can_use_notify",
        },
        {
            "name": "Security",
            "link": "main.security",
        },
        {
            "name": "Terms of use",
            "link": "main.terms",
        },
    ]


def pricing_nav():
    return [
        {
            "name": "Pricing",
            "link": "main.pricing",
        },
        {
            "name": "How to pay",
            "link": "main.how_to_pay",
        },
    ]


def using_notify_nav():
    return [
        {
            "name": "Get started",
            "link": "main.get_started",
        },
        {
            "name": "Trial mode",
            "link": "main.trial_mode_new",
        },
        {
            "name": "Delivery status",
            "link": "main.message_status",
        },
        {
            "name": "Guidance",
            "link": "main.guidance_index",
            "sub_navigation_items": [
                {
                    "name": "Formatting",
                    "link": "main.edit_and_format_messages",
                },
                {
                    "name": "Sending bulk messages",
                    "link": "main.sending_bulk_messages",
                }
            ]
        },
        {
            "name": "API documentation",
            "link": "main.documentation",
        },
    ]
