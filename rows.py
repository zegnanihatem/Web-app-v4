import streamlit as st
import pandas as pd
import numpy as np
from io import BytesIO
from streamlit_option_menu import option_menu
from streamlit_login_auth_ui.widgets import __login__
from Common import to_excel
from st_row_buttons import st_row_buttons



st.set_page_config(
   page_title="Xinlida Catalogue",
   page_icon="🧊",
   layout="wide",
   initial_sidebar_state="expanded",
)

hide_streamlit_style = """
            <style>
            #MainMenu {visibility: hidden;}
            footer {visibility: hidden;}
            </style>
            """
st.markdown(hide_streamlit_style, unsafe_allow_html=True)

__login__obj = __login__(auth_token = "courier_auth_token", 
                    company_name = "XINLIDA",
                    width = 200, height = 250, 
                    logout_button_name = 'Logout', hide_menu_bool = False, 
                    hide_footer_bool = False, 
                    lottie_url = 'https://assets2.lottiefiles.com/packages/lf20_jcikwtux.json')

LOGGED_IN = __login__obj.build_login_ui()

if LOGGED_IN == True:
    st.write('<style>div.block-container{padding-top:0rem;}</style>', unsafe_allow_html=True)

    
    with st.sidebar:
        st.image(r"Data\logo.jpeg")
        menu = option_menu(menu_title="Navigation",options=
                           ["SHIMS",
                            "KITS",
                            ],
                            default_index=1,
                            icons=["gear",
                                   "gear"],

        )
    if menu == "SHIMS":
        page = st_row_buttons(
        # The different pages
        ('Request For Quotation', 'FMSI Lookup', 'SHIM Lookup'),
        # Enable navbar
        nav=True,
        # You can pass a formatting function. Here we capitalize the options
        #format_func=lambda name: name.capitalize(),
        )

        # Display the right things according to the page
        if page == 'Request For Quotation':
            SHIMS_RFQ_Template= pd.read_excel(r'Data\Excels\SHIMS_RFQ_template.xlsx')
            SHIMS_RFQ= st.download_button(label='📥 Download SHIMS RFQ template',
                                data=to_excel(SHIMS_RFQ_Template),
                                file_name= 'SHIMS_RFQ_Template.xlsx')
            RFQ = st.file_uploader("Upload a Request For Quotation")
