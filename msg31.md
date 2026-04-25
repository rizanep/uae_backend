MSG91 WhatsApp API



Common endpoint and header for all the payloads


API URL- 'https://api.msg91.com/api/v5/whatsapp/whatsapp-outbound-message/bulk/'

Method- Post

header 'Content-Type: application/json'

header 'authkey: <authkey>'



Payloads:-


Header


Header with None


{

    "integrated_number": "Your integrated Number",

    "content_type": "template",

    "payload": {

        "messaging_product": "whatsapp",

        "type": "template",

        "template": {

            "name": "WhatsApp Template Name",

            "language": {

                "code": "en",

                "policy": "deterministic"

            },

            "namespace": null,

            "to_and_components": [

                {

                    "to": [

                        "<list_of_phone_numbers>"

                    ],

                    "components": {}

                }

            ]

        }

    }

}


========================================================================


Header with Text


{

    "integrated_number": "Your integrated Number",

    "content_type": "template",

    "payload": {

        "messaging_product": "whatsapp",

        "type": "template",

        "template": {

            "name": "WhatsApp Template Name",

            "language": {

                "code": "en",

                "policy": "deterministic"

            },

            "namespace": null,

            "to_and_components": [

                {

                    "to": [

                        "<list_of_phone_numbers with country code>"

                    ],

                    "components": {}

                }

            ]

        }

    }

}


========================================================================


Header with Image


{

    "integrated_number": "Your integrated Number",

    "content_type": "template",

    "payload": {

        "messaging_product": "whatsapp",

        "type": "template",

        "template": {

            "name": "WhatsApp Template Name",

            "language": {

                "code": "en",

                "policy": "deterministic"

            },

            "namespace": null,

            "to_and_components": [

                {

                    "to": [

                        "<list_of_phone_numbers with country code>"

                    ],

                    "components": {

                        "header_1": {

                            "type": "image",

                            "value": "<url of media>"

                        }

                    }

                }

            ]

        }

    }

}


========================================================================


Header with Video


{

    "integrated_number": "Your integrated Number",

    "content_type": "template",

    "payload": {

        "messaging_product": "whatsapp",

        "type": "template",

        "template": {

            "name": "WhatsApp Template Name",

            "language": {

                "code": "en",

                "policy": "deterministic"

            },

            "namespace": null,

            "to_and_components": [

                {

                    "to": [

                        "<list_of_phone_numbers with country code>"

                    ],

                    "components": {

                        "header_1": {

                            "type": "video",

                            "value": "<url of media>"

                        }

                    }

                }

            ]

        }

    }

}


========================================================================


Header with Document


{

    "integrated_number": "Your integrated Number",

    "content_type": "template",

    "payload": {

        "messaging_product": "whatsapp",

        "type": "template",

        "template": {

            "name": "Template Name",

            "language": {

                "code": "en",

                "policy": "deterministic"

            },

            "namespace": null,

            "to_and_components": [

                {

                    "to": [

                        "<list_of_phone_numbers with country code>"

                    ],

                    "components": {

                        "header_1": {

                            "filename": "<filename>",

                            "type": "document",

                            "value": "<url of media>"

                        }

                    }

                }

            ]

        }

    }

}


========================================================================


Header with Location


{

   "integrated_number": "Your integrated Number",

    "content_type": "template",

    "payload": {

        "messaging_product": "whatsapp",

        "type": "template",

        "template": {

            "name": "Template Name",

            "language": {

                "code": "en",

                "policy": "deterministic"

            },

            "namespace": null,

            "to_and_components": [

                {

                    "to": [

                        "<list_of_phone_numbers>"

                    ],

                    "components": {

                        "header_1_latitude": {

                            "type": "location",

                            "value": "<latitude>"

                        },

                        "header_1_longitude": {

                            "type": "location",

                            "value": "<longitude>"

                        },

                        "header_1_name": {

                            "type": "location",

                            "value": "<name>"

                        },

                        "header_1_address": {

                            "type": "location",

                            "value": "<address>"

                        },

                        "body_1": {

                            "type": "text",

                            "value": "value1"

                        }

                    }

                }

            ]

        }

    }

}

========================================================================

Button

Button with Quick Reply


{

    "integrated_number": "Your WhatsApp Integrated number",

    "content_type": "template",

    "payload": {

        "messaging_product": "whatsapp",

        "type": "template",

        "template": {

            "name": "WhatsApp Template Name",

            "language": {

                "code": "en",

                "policy": "deterministic"

            },

            "namespace": null,

            "to_and_components": [

                {

                    "to": [

                        "<list_of_phone_numbers>"

                    ],

                    "components": {}

                }

            ]

        }

    }

}


Button With Website Link:

{

    "integrated_number": "Your WhatsApp Integrated number",

    "content_type": "template",

    "payload": {

        "messaging_product": "whatsapp",

        "type": "template",

        "template": {

            "name": "WhatsApp Template Name",

            "language": {

                "code": "en",

                "policy": "deterministic"

            },

            "namespace": null,

            "to_and_components": [

                {

                    "to": [

                        "<list_of_phone_numbers>"

                    ],

                    "components": {}

                }

            ]

        }

    }

}



Button with phone number and website link:

{

    "integrated_number": "Your WhatsApp Integrated number",

    "content_type": "template",

    "payload": {

        "messaging_product": "whatsapp",

        "type": "template",

        "template": {

            "name": "WhatsApp Template Name",

            "language": {

                "code": "en_GB",

                "policy": "deterministic"

            },

            "namespace": null,

            "to_and_components": [

                {

                    "to": [

                        "<list_of_phone_numbers>"

                    ],

                    "components": {

                        "header_1": {

                            "type": "image",

                            "value": "<url of media>"

                        },

                        "body_1": {

                            "type": "text",

                            "value": "value1"

                        },

                        "body_2": {

                            "type": "text",

                            "value": "value1"

                        },

                        "body_3": {

                            "type": "text",

                            "value": "value1"

                        }

                    }

                }

            ]

        }

    }

}



Copy code button in template:

{

    "integrated_number": "Your WhatsApp Integrated number",

    "content_type": "template",

    "payload": {

        "messaging_product": "whatsapp",

        "type": "template",

        "template": {

            "name": "WhatsApp Template Name",

            "language": {

                "code": "en_US",

                "policy": "deterministic"

            },

            "namespace": null,

            "to_and_components": [

                {

                    "to": [

                        "<list_of_phone_numbers>"

                    ],

                    "components": {

                        "body_1": {

                            "type": "text",

                            "value": "value1"

                        },

                        "button_1": {

                            "subtype": "url",

                            "type": "text",

                            "value": "<{{url text variable}}>"

                        }

                    }

                }

            ]

        }

    }

}






Header with Button

1). Header (Text) - Variable
Body (Text) - Variable
CTA button (Visit Website)  - Variable or click count enabled
{

    "integrated_number": "Your integrated Number",

    "content_type": "template",

    "payload": {

        "messaging_product": "whatsapp",

        "type": "template",

        "template": {

            "name": "Your template name",

            "language": {

                "code": "en",

                "policy": "deterministic"

            },

            "namespace": null,

            "to_and_components": [

                {

                    "to": [

                        "<list_of_phone_numbers>"

                    ],

                    "components": {

                        "header_1": {

                            "type": "text",

                            "value": "<{{1}}>"

                        },

                        "body_1": {

                            "type": "text",

                            "value": "value1"

                        },

                        "button_1": {

                            "subtype": "url",

                            "type": "text",

                            "value": "<{{url text variable}}>"

                        }

                    }

                }

            ]

        }

    }

}


========================================================================


2) Header (Image)
Body (Text) - Variable
CTA button (Visit Website) - Variable or click count enabled

{

    "integrated_number": "Your integrated Number",

    "content_type": "template",

    "payload": {

        "messaging_product": "whatsapp",

        "type": "template",

        "template": {

            "name": "Your template name",

            "language": {

                "code": "en",

                "policy": "deterministic"

            },

            "namespace": null,

            "to_and_components": [

                {

                    "to": [

                        "<list_of_phone_numbers>"

                    ],

                    "components": {

                        "header_1": {

                            "type": "image",

                            "value": "<url of media>"

                        },

                        "body_1": {

                            "type": "text",

                            "value": "value1"

                        },

                        "button_1": {

                            "subtype": "url",

                            "type": "text",

                            "value": "<{{url text variable}}>"

                        }

                    }

                }

            ]

        }

    }

}

========================================================================


3). Header (Video)
Body (Text) - Variable
CTA button (Visit Website)  - Variable or click count enabled

{

    "integrated_number": "Your integrated Number",

    "content_type": "template",

    "payload": {

        "messaging_product": "whatsapp",

        "type": "template",

        "template": {

            "name": "Your template name",

            "language": {

                "code": "en",

                "policy": "deterministic"

            },

            "namespace": null,

            "to_and_components": [

                {

                    "to": [

                        "<list_of_phone_numbers>"

                    ],

                    "components": {

                        "header_1": {

                            "type": "video",

                            "value": "<url of media>"

                        },

                        "body_1": {

                            "type": "text",

                            "value": "value1"

                        },

                        "button_1": {

                            "subtype": "url",

                            "type": "text",

                            "value": "<{{url text variable}}>"

                        }

                    }

                }

            ]

        }

    }

}


========================================================================


4).Header (Document)
Body (Text) - Variable
CTA button (Visit Website)  - Variable or click count enabled

{

    "integrated_number": "Your integrated Number",

    "content_type": "template",

    "payload": {

        "messaging_product": "whatsapp",

        "type": "template",

        "template": {

            "name": "Your template name",

            "language": {

                "code": "en",

                "policy": "deterministic"

            },

            "namespace": null,

            "to_and_components": [

                {

                    "to": [

                        "<list_of_phone_numbers>"

                    ],

                    "components": {

                        "header_1": {

                            "filename": "<filename>",

                            "type": "document",

                            "value": "<url of media>"

                        },

                        "body_1": {

                            "type": "text",

                            "value": "value1"

                        },

                        "button_1": {

                            "subtype": "url",

                            "type": "text",

                            "value": "<{{url text variable}}>"

                        }

                    }

                }

            ]

        }

    }

}


========================================================================


5). Header (Location)
Body (Text) - Variable
CTA button (Visit Website)  - Variable or click count enabled


{

    "integrated_number": "Your integrated Number",

    "content_type": "template",

    "payload": {

        "messaging_product": "whatsapp",

        "type": "template",

        "template": {

            "name": "Your template name",

            "language": {

                "code": "en",

                "policy": "deterministic"

            },

            "namespace": null,

            "to_and_components": [

                {

                    "to": [

                        "<list_of_phone_numbers>"

                    ],

                    "components": {

                        "header_1_latitude": {

                            "type": "location",

                            "value": "<latitude>"

                        },

                        "header_1_longitude": {

                            "type": "location",

                            "value": "<longitude>"

                        },

                        "header_1_name": {

                            "type": "location",

                            "value": "<name>"

                        },

                        "header_1_address": {

                            "type": "location",

                            "value": "<address>"

                        },

                        "body_1": {

                            "type": "text",

                            "value": "value1"

                        },

                        "button_1": {

                            "subtype": "url",

                            "type": "text",

                            "value": "<{{url text variable}}>"

                        }

                    }

                }

            ]

        }

    }

}


========================================================================


6). Header (Text) - Variable
Body (Text) - Variable
CTA button (Copy offer code)

{

   "integrated_number": "Your integrated Number",

    "content_type": "template",

    "payload": {

        "messaging_product": "whatsapp",

        "type": "template",

        "template": {

           "name": "Your template name",

            "language": {

                "code": "en",

                "policy": "deterministic"

            },

            "namespace": null,

            "to_and_components": [

                {

                    "to": [

                        "<list_of_phone_numbers>"

                    ],

                    "components": {

                        "header_1": {

                            "type": "text",

                            "value": "<{{1}}>"

                        },

                        "body_1": {

                            "type": "text",

                            "value": "value1"

                        },

                        "button_1": {

                            "type": "coupon_code",

                            "coupon_code": "<COUPON_CODE>",

                            "subtype": "COPY_CODE"

                        }

                    }

                }

            ]

        }

    }

}


========================================================================


7). Header (Image)
Body (Text) - Variable
CTA button (Copy offer code)

{

    "integrated_number": "Your integrated Number",

    "content_type": "template",

    "payload": {

        "messaging_product": "whatsapp",

        "type": "template",

        "template": {

            "name": "Your template name",

            "language": {

                "code": "en",

                "policy": "deterministic"

            },

            "namespace": null,

            "to_and_components": [

                {

                    "to": [

                        "<list_of_phone_numbers>"

                    ],

                    "components": {

                        "header_1": {

                            "type": "image",

                            "value": "<url of media>"

                        },

                        "body_1": {

                            "type": "text",

                            "value": "value1"

                        },

                        "button_1": {

                            "type": "coupon_code",

                            "coupon_code": "<COUPON_CODE>",

                            "subtype": "COPY_CODE"

                        }

                    }

                }

            ]

        }

    }

}


========================================================================


8). Header (Video)
Body (Text) - Variable
CTA button (Copy offer code)

{

    "integrated_number": "Your integrated Number",

    "content_type": "template",

    "payload": {

        "messaging_product": "whatsapp",

        "type": "template",

        "template": {

            "name": "Your template name",

            "language": {

                "code": "en",

                "policy": "deterministic"

            },

            "namespace": null,

            "to_and_components": [

                {

                    "to": [

                        "<list_of_phone_numbers>"

                    ],

                    "components": {

                        "header_1": {

                            "type": "video",

                            "value": "<url of media>"

                        },

                        "body_1": {

                            "type": "text",

                            "value": "value1"

                        },

                        "button_1": {

                            "type": "coupon_code",

                            "coupon_code": "<COUPON_CODE>",

                            "subtype": "COPY_CODE"

                        }

                    }

                }

            ]

        }

    }

}


========================================================================


9). Header (Document)
Body (Text) - Variable
CTA button (Copy offer code)

{

    "integrated_number": "Your integrated Number",

    "content_type": "template",

    "payload": {

        "messaging_product": "whatsapp",

        "type": "template",

        "template": {

            "name": "Your template name",

            "language": {

                "code": "en",

                "policy": "deterministic"

            },

            "namespace": null,

            "to_and_components": [

                {

                    "to": [

                        "<list_of_phone_numbers>"

                    ],

                    "components": {

                        "header_1": {

                            "filename": "<filename>",

                            "type": "document",

                            "value": "<url of media>"

                        },

                        "body_1": {

                            "type": "text",

                            "value": "value1"

                        },

                        "button_1": {

                            "type": "coupon_code",

                            "coupon_code": "<COUPON_CODE>",

                            "subtype": "COPY_CODE"

                        }

                    }

                }

            ]

        }

    }

}


========================================================================


10). Header (Location)
Body (Text) - Variable
CTA button (Copy offer code)


{

    "integrated_number": "Your integrated Number",

    "content_type": "template",

    "payload": {

        "messaging_product": "whatsapp",

        "type": "template",

        "template": {

            "name": "Your template name",

            "language": {

                "code": "en",

                "policy": "deterministic"

            },

            "namespace": null,

            "to_and_components": [

                {

                    "to": [

                        "<list_of_phone_numbers>"

                    ],

                    "components": {

                        "header_1_latitude": {

                            "type": "location",

                            "value": "<latitude>"

                        },

                        "header_1_longitude": {

                            "type": "location",

                            "value": "<longitude>"

                        },

                        "header_1_name": {

                            "type": "location",

                            "value": "<name>"

                        },

                        "header_1_address": {

                            "type": "location",

                            "value": "<address>"

                        },

                        "body_1": {

                            "type": "text",

                            "value": "value1"

                        },

                       "button_1": {

                            "type": "coupon_code",

                            "coupon_code": "<COUPON_CODE>",

                            "subtype": "COPY_CODE"

                        }

                    }

                }

            ]

        }

    }

}


========================================================================


11). Header (Text) - Variable

Body (Text) - Variable
CTA button 1 (Visit Website) -  - Variable or click count enabled

CTA button 2 (Copy offer code)


{

   "integrated_number": "Your integrated Number",

    "content_type": "template",

    "payload": {

        "messaging_product": "whatsapp",

        "type": "template",

        "template": {

           "name": "Your template name",

            "language": {

                "code": "en",

                "policy": "deterministic"

            },

            "namespace": null,

            "to_and_components": [

                {

                    "to": [

                        "<list_of_phone_numbers>"

                    ],

                    "components": {

                        "header_1": {

                            "type": "text",

                            "value": "<{{1}}>"

                        },

                        "body_1": {

                            "type": "text",

                            "value": "value1"

                        },

                        "button_1": {

                            "subtype": "url",

                            "type": "text",

                            "value": "<{{url text variable}}>"

                        },

                        "button_2": {

                            "type": "coupon_code",

                            "coupon_code": "<COUPON_CODE>",

                            "subtype": "COPY_CODE"

                        }

                    }

                }

            ]

        }

    }

}


========================================================================


12).

Header (Image)

Body (Text) - variable
CTA button 1 (Visit Website) - Variable or click count enabled  

CTA button 2 (Copy offer code)


{

   "integrated_number": "Your integrated Number",

    "content_type": "template",

    "payload": {

        "messaging_product": "whatsapp",

        "type": "template",

        "template": {

           "name": "Your template name",

            "language": {

                "code": "en",

                "policy": "deterministic"

            },

            "namespace": null,

            "to_and_components": [

                {

                    "to": [

                        "<list_of_phone_numbers>"

                    ],

                    "components": {

                        "header_1": {

                            "type": "image",

                            "value": "<url of media>"

                        },

                        "body_1": {

                            "type": "text",

                            "value": "value1"

                        },

                        "button_1": {

                            "subtype": "url",

                            "type": "text",

                            "value": "<{{url text variable}}>"

                        },

                        "button_2": {

                            "type": "coupon_code",

                            "coupon_code": "<COUPON_CODE>",

                            "subtype": "COPY_CODE"

                        }

                    }

                }

            ]

        }

    }

}


========================================================================


13). Header (Video)

Body (Text) - Variable

CTA button 1 (Visit Website) - Variable or click count enabled

CTA button 2 (Copy offer code)


{

   "integrated_number": "Your integrated Number",

    "content_type": "template",

    "payload": {

        "messaging_product": "whatsapp",

        "type": "template",

        "template": {

           "name": "Your template name",

            "language": {

                "code": "en",

                "policy": "deterministic"

            },

            "namespace": null,

            "to_and_components": [

                {

                    "to": [

                        "<list_of_phone_numbers>"

                    ],

                    "components": {

                        "header_1": {

                            "type": "video",

                            "value": "<url of media>"

                        },

                        "body_1": {

                            "type": "text",

                            "value": "value1"

                        },

                        "button_1": {

                            "subtype": "url",

                            "type": "text",

                            "value": "<{{url text variable}}>"

                        },

                        "button_2": {

                            "type": "coupon_code",

                            "coupon_code": "<COUPON_CODE>",

                            "subtype": "COPY_CODE"

                        }

                    }

                }

            ]

        }

    }

}


========================================================================


14). Header (Document)

Body (Text) - Variable

CTA button 1 (Visit Website) - Variable or click count enabled

CTA button 2 (Copy offer code)


{

   "integrated_number": "Your integrated Number",

    "content_type": "template",

    "payload": {

        "messaging_product": "whatsapp",

        "type": "template",

        "template": {

           "name": "Your template name",

            "language": {

                "code": "en",

                "policy": "deterministic"

            },

            "namespace": null,

            "to_and_components": [

                {

                    "to": [

                        "<list_of_phone_numbers>"

                    ],

                    "components": {

                        "header_1": {

                            "filename": "<filename>",

                            "type": "document",

                            "value": "<url of media>"

                        },

                        "body_1": {

                            "type": "text",

                            "value": "value1"

                        },

                        "button_1": {

                            "subtype": "url",

                            "type": "text",

                            "value": "<{{url text variable}}>"

                        },

                        "button_2": {

                            "type": "coupon_code",

                            "coupon_code": "<COUPON_CODE>",

                            "subtype": "COPY_CODE"

                        }

                    }

                }

            ]

        }

    }

}


========================================================================


15 ). Header (Location)

Body (Text) - Variable

CTA button 1 (Visit Website)  - Variable or click count enabled

CTA button 2 (Copy offer code)


{

  "integrated_number": "Your integrated Number",

    "content_type": "template",

    "payload": {

        "messaging_product": "whatsapp",

        "type": "template",

        "template": {

          "name": "Your template name",

            "language": {

                "code": "en",

                "policy": "deterministic"

            },

            "namespace": null,

            "to_and_components": [

                {

                    "to": [

                        "<list_of_phone_numbers>"

                    ],

                    "components": {

                        "header_1_latitude": {

                            "type": "location",

                            "value": "<latitude>"

                        },

                        "header_1_longitude": {

                            "type": "location",

                            "value": "<longitude>"

                        },

                        "header_1_name": {

                            "type": "location",

                            "value": "<name>"

                        },

                        "header_1_address": {

                            "type": "location",

                            "value": "<address>"

                        },

                        "body_1": {

                            "type": "text",

                            "value": "value1"

                        },

                        "button_1": {

                            "subtype": "url",

                            "type": "text",

                            "value": "<{{url text variable}}>"

                        },

                        "button_2": {

                            "type": "coupon_code",

                            "coupon_code": "<COUPON_CODE>",

                            "subtype": "COPY_CODE"

                        }

                    }

                }

            ]

        }

    }

}



NOTE : If the Header Or Body has no variable text then you don’t need to mention the header component or body component in the payload

Authentication

Authentication Template code


{

    "integrated_number": "Your integrated Numberr",

    "content_type": "template",

    "payload": {

        "messaging_product": "whatsapp",

        "type": "template",

        "template": {

            "name": "WhatsApp Template Name",

            "language": {

                "code": "hi",

                "policy": "deterministic"

            },

            "namespace": null,

            "to_and_components": [

                {

                    "to": [

                        "<list_of_phone_numbers with country code>"

                    ],

                    "components": {

                        "body_1": {

                            "type": "text",

                            "value": "value1"

                        },

                        "button_1": {

                            "subtype": "url",

                            "type": "text",

                            "value": "<{{url text variable}}>"

                        }

                    }

                }

            ]

        }

    }

}

Footer

Without Footer


{

    "integrated_number": "Your WhatsApp Integrated number",

    "content_type": "template",

    "payload": {

        "messaging_product": "whatsapp",

        "type": "template",

        "template": {

            "name": "WhatsApp Template Name",

            "language": {

                "code": "en",

                "policy": "deterministic"

            },

            "namespace": null,

            "to_and_components": [

                {

                    "to": [

                        "<list_of_phone_numbers>"

                    ],

                    "components": {}

                }

            ]

        }

    }

}


========================================================================


With Footer


{

    "integrated_number": "Your WhatsApp Integrated number",

    "content_type": "template",

    "payload": {

        "messaging_product": "whatsapp",

        "type": "template",

        "template": {

            "name": "WhatsApp Template Name",

            "language": {

                "code": "en",

                "policy": "deterministic"

            },

            "namespace": null,

            "to_and_components": [

                {

                    "to": [

                        "<list_of_phone_numbers>"

                    ],

                    "components": {}

                }

            ]

        }

    }

}


========================================================================

Carousel

Carousel with Custom button (media type- Image)

{

    "integrated_number": "your integrated number",

    "content_type": "template",

    "payload": {

        "messaging_product": "whatsapp",

        "type": "template",

        "template": {

            "name": "template name",

            "language": {

                "code": "en_GB",

                "policy": "deterministic"

            },

            "namespace": null,

            "to_and_components": [

                {

                    "to": [

                        "<list_of_phone_numbers>"

                    ],

                    "components": {

                      "body_1": {

                            "type": "text",

                            "value": "value1"

                        },


                        "card_0_header_1": {

                            "type": "image",

                            "value": "<url of media>"

                        }

                    }

                }

            ]

        }

    }

}


========================================================================


2. Carousel with custom button (Media type - video)


{

    "integrated_number": "your integrated number",

    "content_type": "template",

    "payload": {

        "messaging_product": "whatsapp",

        "type": "template",

        "template": {

            "name": "template name",

            "language": {

                "code": "en_GB",

                "policy": "deterministic"

            },

            "namespace": null,

            "to_and_components": [

                {

                    "to": [

                        "<list_of_phone_numbers>"

                    ],

                    "components": {

                        "card_0_header_1": {

                            "type": "video",

                            "value": "<url of media>"

                        }

                    }

                }

            ]

        }

    }

}


========================================================================


3. Carousel with Button of Call phone number (media type -Image)


{

    "integrated_number": "your integrated number",

    "content_type": "template",

    "payload": {

        "messaging_product": "whatsapp",

        "type": "template",

        "template": {

            "name": "template name",

            "language": {

                "code": "en_GB",

                "policy": "deterministic"

            },

            "namespace": null,

            "to_and_components": [

                {

                    "to": [

                        "<list_of_phone_numbers>"

                    ],

                    "components": {

                        "body_1": {

                            "type": "text",

                            "value": "value1"

                        },


                        "card_0_header_1": {

                            "type": "image",

                            "value": "<url of media>"

                        }

                    }

                }

            ]

        }

    }

}


========================================================================


4. Carousel with Button of Call phone number (media type -Video)


{

    "integrated_number": "your integrated number",

    "content_type": "template",

    "payload": {

        "messaging_product": "whatsapp",

        "type": "template",

        "template": {

            "name": "template name",

            "language": {

                "code": "en_GB",

                "policy": "deterministic"

            },

            "namespace": null,

            "to_and_components": [

                {

                    "to": [

                        "<list_of_phone_numbers>"

                    ],

                    "Components":

               {

                 "body_1": {

                            "type": "text",

                            "value": "value1"

                        },

                        "card_0_header_1": {

                            "type": "video",

                            "value": "<url of media>"

                        }

                    }

                }

            ]

        }

    }

}


========================================================================


5. Carousel with Button to Visit website  (media type- Image)


{

    "integrated_number": "your integrated number",

    "content_type": "template",

    "payload": {

        "messaging_product": "whatsapp",

        "type": "template",

        "template": {

            "name": "template_name",

            "language": {

                "code": "en_GB",

                "policy": "deterministic"

            },

            "namespace": null,

            "to_and_components": [

                {

                    "to": [

                        "<list_of_phone_numbers>"

                    ],

                    "components": {

                        "card_0_header_1": {

                            "type": "image",

                            "value": "<url of media>"

                        }

                    }

                }

            ]

        }

    }

}


========================================================================


6. Carousel with Button to Visit website  (media type- Video)


{

    "integrated_number": "your integrated number",

    "content_type": "template",

    "payload": {

        "messaging_product": "whatsapp",

        "type": "template",

        "template": {

            "name": "template name",

            "language": {

                "code": "en_GB",

                "policy": "deterministic"

            },

            "namespace": null,

            "to_and_components": [

                {

                    "to": [

                        "<list_of_phone_numbers>"

                    ],

                    "components": {

                        "card_0_header_1": {

                            "type": "video",

                            "value": "<url of media>"

                        }

                    }

                }

            ]

        }

    }

}


========================================================================



Catalogue

Product catalogue


{

    "integrated_number": "Your Integrated Number",

    "content_type": "template",

    "payload": {

        "messaging_product": "whatsapp",

        "type": "template",

        "template": {

            "name": "WhatsApp Template Name",

            "language": {

                "code": "en",

                "policy": "deterministic"

            },

            "namespace": null,

            "to_and_components": [

                {

                    "to": [

                        "<list_of_phone_numbers>"

                    ],

                    "components": {

                        "button_1": {

                            "subtype": "CATALOG",

                            "type": "action",

                            "value": "<product retailer id>"

                        }

                    }

                }

            ]

        }

    }

}


========================================================================


Multiple Product Catalogue


{

    "integrated_number": "Your Integrated Number",

    "content_type": "template",

    "payload": {

        "messaging_product": "whatsapp",

        "type": "template",

        "template": {

            "name": "WhatsApp Template Name",

            "language": {

                "code": "en",

                "policy": "deterministic"

            },

            "namespace": null,

            "to_and_components": [

                {

                    "to": [

                        "<list_of_phone_numbers>"

                    ],

                    "components": {

                        "button_1": {

                            "subtype": "MPM",

                            "type": "action",

                            "value": {

                                "thumbnail_product_retailer_id": "<thumbnail_product_retailer_id>",

                                "sections": [

                                    {

                                        "title": "<section_title>",

                                        "product_items": [

                                            {

                                                "product_retailer_id": "<product retailer id>"

                                            },

                                            {

                                                "product_retailer_id": "<product retailer id>"

                                            }

                                        ]

                                    }

                                ]

                            }

                        }

                    }

                }

            ]

        }

    }

}


========================================================================