import streamlit as st
import pandas as pd
from streamlit_option_menu import option_menu
from streamlit_login_auth_ui.widgets import __login__
from Common import to_excel
from st_row_buttons import st_row_buttons
import re
import os



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
    
    DB_path= "Data/Excels/Database.xlsx"
    @st.cache
    def load_DB(DB_path):
        Sheets= pd.read_excel(DB_path, sheet_name=["FMSI", "Kits", "Shim_crossing", "Kit_crossing", "SHIMS"])
        FMSI= Sheets['FMSI']
        SHIMS= Sheets['SHIMS']
        Kits= Sheets['Kits']
        Shim_crossing= Sheets['Shim_crossing']
        Kit_crossing= Sheets['Kit_crossing']

        FMSI= FMSI.astype(str)
        Shim_crossing= Shim_crossing.astype(str)

        Flat_SHIMS= FMSI.merge(Shim_crossing, on= 'FMSI').merge(SHIMS, on= 'SHIM PN')
        Flat_kits= FMSI.merge(Kit_crossing, on= 'FMSI').merge(Kits, on= 'KIT PN')
        return Flat_SHIMS, Flat_kits, FMSI, SHIMS, Kits, Shim_crossing, Kit_crossing
    
    Flat_SHIMS, Flat_kits, FMSI, SHIMS, Kits, Shim_crossing, Kit_crossing= load_DB(DB_path)
    
    
    with st.sidebar:
        st.image(r"Data/logo.jpeg")
        menu = option_menu(menu_title="Navigation",options=
                           ["SHIMS",
                            "KITS",
                            "RAW DATA"
                            ],
                            default_index=1,
                            #icons=["gear",
                            #       "gear"],

        )
    if menu == "SHIMS":
        st.write("# SHIMS Catalogue")
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
            SHIMS_RFQ_Template= pd.read_excel(r'Data/Excels/SHIMS_RFQ_template.xlsx')
            SHIMS_RFQ= st.download_button(label='📥 Download SHIMS RFQ template',
                                data=to_excel(SHIMS_RFQ_Template),
                                file_name= 'SHIMS_RFQ_Template.xlsx')
            file = st.file_uploader("Upload a Request For Quotation (following above template)")

            if file:
                RFQ=pd.read_excel(file)
                try:
                    valid_headers= (SHIMS_RFQ_Template.columns==RFQ.columns).min()
                except:
                    valid_headers= 0
                if not valid_headers :
                    st.write('Invalid file format: ')
                    for column in SHIMS_RFQ_Template.columns:
                        if column not in RFQ.columns:
                            st.write("'", column ,"' column is missing")
                elif valid_headers:
                    RFQ['Flat or Tabbed']= RFQ['Flat or Tabbed'].map({'Flat': 'Staked', 'Tabbed': 'Tabbed'})
                    st.markdown("## RFQ Data loaded:")
                    st.dataframe(RFQ)
                    
                    #Extract FMSI numbers
                    FMSI_matches= RFQ['D Plate Number'].str.extractall(r'(D\d+)')
                    FMSI_matches.rename({0: 'FMSI'}, axis= 1, inplace= True)
                    FMSI_matches.index.rename(['line', 'match'], inplace= True)
                    
                    FMSI_matches['FMSI (short)']= FMSI_matches['FMSI'].apply(lambda s: re.sub(r'^D0*', 'D', s) )
                    for i in RFQ.index:
                        FMSI_matches.loc[i, 'Flat or Tabbed']= RFQ.loc[i, 'Flat or Tabbed']
                    st.markdown('## Extracted FMSI plate numbers: ')
                    st.dataframe(FMSI_matches)

                    #RFQ Full match
                    st.markdown('## Full match:')

                    SubResults= []
                    for line in FMSI_matches.index.get_level_values('line'):
                        line_results=[]
                        Flat_or_tabbed= FMSI_matches.loc[(line,0),"Flat or Tabbed"]
                        for match in FMSI_matches.loc[line, 'FMSI (short)']:
                            
                            temp_df= Flat_SHIMS[(Flat_SHIMS['FMSI (short)']==match) & (Flat_SHIMS['ATTACHMENT METHOD']==Flat_or_tabbed)]
                            temp_df.drop('LINK TYPE', axis= 1).drop_duplicates(inplace= True)
                            temp_df= Flat_SHIMS[Flat_SHIMS['FMSI (short)']==match]
                            line_results.append(set(temp_df["SHIM PN"].values))
                        result= line_results[0].intersection(*line_results)
                        Result_df= Flat_SHIMS.loc[(Flat_SHIMS['SHIM PN'].isin(result)) 
                                                    & (Flat_SHIMS['FMSI (short)'].isin(FMSI_matches.loc[line, 'FMSI (short)']))
                                                    & (Flat_SHIMS["ATTACHMENT METHOD"]==Flat_or_tabbed)]
                        Result_df= Result_df.drop('LINK TYPE', axis= 1).drop_duplicates()
                        Result_df['Line']= line
                        Result_df.set_index(['Line', 'SHIM PN', 'FMSI (short)'], inplace= True)
                        SubResults.append(Result_df)
                        
                    Output= pd.concat(SubResults)
                    Output= Output.reset_index().drop_duplicates()
                    Output['Cost']= "$"
                    short_RFQ= RFQ.reset_index().rename(columns={"index":"Line"})[['Line', 'D Plate Number']].set_index("Line")
                    Output= Output.set_index('Line').join(short_RFQ).reset_index()

                    Output= Output[['Line','D Plate Number','ATTACHMENT METHOD','FMSI (short)', 'SHIM PN', 'COO','Cost', 'FMSI', 'FMSI 2', 'US CA UIO',
                                    'US CA MX UIO', 'US 1 Year Grow Rate', 'Avg Age', 'Comment',
                                    'Application(s)', 'COMMENT_x', 'CREATION DATE', 'LAST UPDATE',
                                    'COMMENT_y', 'OAW', 'OAH', '# of holes',
                                    '# of top tabs', '# of bottom tabs',
                                    'Wrap Around Design (End, Under, Both, None)', 'Reviewed Dwg. Date',
                                    'Reviewed Dwg. Rev Level']]
                    st.dataframe(Output)
                    df_xlsx = to_excel(Output.reset_index())
                    st.download_button(label='📥 Download full match',
                                                    data=df_xlsx ,
                                                    file_name= 'RFQ_output.xlsx')
                    #Partial match
                    st.markdown('## Partial match:')
                    SubResults= []
                    for line in FMSI_matches.index.get_level_values('line'):
                        line_results=[]
                        Flat_or_tabbed= FMSI_matches.loc[(line,0),"Flat or Tabbed"]
                        for match in FMSI_matches.loc[line, 'FMSI (short)']:
                            
                            temp_df= Flat_SHIMS[(Flat_SHIMS['FMSI (short)']==match) & (Flat_SHIMS['ATTACHMENT METHOD']==Flat_or_tabbed)]
                            temp_df.drop('LINK TYPE', axis= 1).drop_duplicates(inplace= True)
                            temp_df= Flat_SHIMS[Flat_SHIMS['FMSI (short)']==match]
                            line_results.append(set(temp_df["SHIM PN"].values))
                        result1= line_results[0].intersection(*line_results)
                        result2= line_results[0].union(*line_results)
                        result= result2.difference(result1)
                        Result_df= Flat_SHIMS.loc[(Flat_SHIMS['SHIM PN'].isin(result)) 
                                                    & (Flat_SHIMS['FMSI (short)'].isin(FMSI_matches.loc[line, 'FMSI (short)']))
                                                    & (Flat_SHIMS["ATTACHMENT METHOD"]==Flat_or_tabbed)]
                        Result_df= Result_df.drop('LINK TYPE', axis= 1).drop_duplicates()
                        Result_df['Line']= line
                        Result_df.set_index(['Line', 'SHIM PN', 'FMSI (short)'], inplace= True)
                        SubResults.append(Result_df)
                        
                        
                    Output_inc= pd.concat(SubResults)
                    Output_inc= Output_inc.reset_index().drop_duplicates().set_index(['Line', 'SHIM PN', 'FMSI (short)'])

                    count_matches=Output_inc.reset_index()
                    count_matches=count_matches.groupby(['Line', 'SHIM PN']).count()['FMSI (short)'].reset_index().set_index("Line")
                    count_per_line= FMSI_matches.reset_index().groupby('line').count()['match']

                    partial_match= count_matches.join(count_per_line, how='left')
                    partial_match['match count']= pd.DataFrame(partial_match['FMSI (short)'].apply(str)+"/"+partial_match['match'].apply(str))
                    partial_match=partial_match.reset_index().rename(columns={"index": "Line"})[['Line', 'SHIM PN', 'match count']]
                    partial_match=partial_match.set_index(['Line', 'SHIM PN'])

                    Output_inc= Output_inc.reset_index().set_index(['Line', 'SHIM PN']).join(partial_match).reset_index()

                    short_RFQ= RFQ.reset_index().rename(columns={"index":"Line"})[['Line', 'D Plate Number']].set_index("Line")
                    Output_inc= Output_inc.set_index('Line').join(short_RFQ).reset_index()

                    
                    Output_inc['Cost']="$"
                    Output_inc= Output_inc[['Line',"D Plate Number",'ATTACHMENT METHOD', 'FMSI (short)', 'SHIM PN','match count' ,'COO', "Cost",
                        'FMSI', 'FMSI 2', 'US CA UIO',
                        'US CA MX UIO', 'US 1 Year Grow Rate', 'Avg Age', 'Comment',
                        'Application(s)', 'COMMENT_x', 'CREATION DATE', 'LAST UPDATE', 
                        'COMMENT_y', 'OAW', 'OAH', '# of holes',
                        '# of top tabs', '# of bottom tabs',
                        'Wrap Around Design (End, Under, Both, None)', 'Reviewed Dwg. Date',
                        'Reviewed Dwg. Rev Level']]
                    
                    st.dataframe(Output_inc)

                    df_xlsx2 = to_excel(Output_inc.reset_index())
                    st.download_button(label='📥 Download partial match',
                                                    data=df_xlsx2 ,
                                                    file_name= 'RFQ_output_partial.xlsx')

                    #No match
                    st.markdown('## No match:')
                    temp_Output= pd.concat([Output, Output_inc]).reset_index().set_index(['Line', 'FMSI (short)'])
                    temp_match= FMSI_matches.reset_index().set_index(['line', 'FMSI (short)'])
                    Output_index= temp_Output.index
                    Match_index= temp_match.index

                    key_diff = set(Match_index).difference(Output_index)
                    where_diff = temp_match.index.isin(key_diff)
                    Not_found= temp_match[where_diff].reset_index()

                    st.dataframe(Not_found)
                    df_xlsx3 = to_excel(Not_found.reset_index())
                    st.download_button(label='📥 Download no match',
                                                    data=df_xlsx2 ,
                                                    file_name= 'RFQ_output_no_match.xlsx')
        if page == "FMSI Lookup":
            FMSI= st.text_input(label= 'FMSI')
            FMSIs= FMSI.split(', ')
            FMSIs= [re.sub(r'^D0*', 'D', s) for s in FMSIs]
            result= Flat_SHIMS[Flat_SHIMS['FMSI (short)'].isin(FMSIs)]
            result= result.drop_duplicates().sort_values(['FMSI', "SHIM PN"]).reset_index()
            result= result[[
                "FMSI",
                "FMSI (short)",
                "FMSI 2",
                "SHIM PN",
                "LINK TYPE",
                "ATTACHMENT METHOD",
                "US CA UIO",
                "US CA MX UIO",
                "US 1 Year Grow Rate",
                "Avg Age",
                "Comment",
                "Application(s)",
                "COMMENT_x",
                "CREATION DATE",
                "LAST UPDATE",
                "COMMENT_y",
                "OAW",
                "OAH",
                "# of holes",
                "# of top tabs",
                "# of bottom tabs",
                "Wrap Around Design (End, Under, Both, None)",
                "Reviewed Dwg. Date",
                "Reviewed Dwg. Rev Level",
                "COO"
            ]]
            result.style.format({
                'US 1 Year Grow Rate': '{:,.2%}'.format,
            })
            st.dataframe(result)
            df_xlsx = to_excel(result.reset_index())
            st.download_button(label='📥 Download Lookup results',
                                            data=df_xlsx ,
                                            file_name= 'FMSI_Lookup_results.xlsx')

        if page == "SHIM Lookup":
            SHIMs= st.text_input(label= 'SHIM')
            SHIMs= SHIMs.split(', ')
            result= Flat_SHIMS[Flat_SHIMS['SHIM PN'].isin(SHIMs)]
            result= result.drop_duplicates().sort_values(["SHIM PN", 'FMSI']).reset_index()
            result= result[[
                "SHIM PN",
                "FMSI",
                "FMSI (short)",
                "FMSI 2",
                "LINK TYPE",
                "ATTACHMENT METHOD",
                "US CA UIO",
                "US CA MX UIO",
                "US 1 Year Grow Rate",
                "Avg Age",
                "Comment",
                "Application(s)",
                "COMMENT_x",
                "CREATION DATE",
                "LAST UPDATE",
                "COMMENT_y",
                "OAW",
                "OAH",
                "# of holes",
                "# of top tabs",
                "# of bottom tabs",
                "Wrap Around Design (End, Under, Both, None)",
                "Reviewed Dwg. Date",
                "Reviewed Dwg. Rev Level",
                "COO"
            ]]
            st.dataframe(result)
            df_xlsx = to_excel(result.reset_index())
            st.download_button(label='📥 Download Lookup results',
                                            data=df_xlsx ,
                                            file_name= 'SHIM_Lookup_results.xlsx')

    if menu == "KITS":
        st.write("# KITS Catalogue")
        page = st_row_buttons(
        # The different pages
        ('Request For Quotation', 'FMSI Lookup', 'KIT Lookup', "KIT images"),
        # Enable navbar
        nav=True,
        # You can pass a formatting function. Here we capitalize the options
        #format_func=lambda name: name.capitalize(),
        )
        if page == 'Request For Quotation':
            KITS_RFQ_Template= pd.read_excel(r'Data/Excels/KITS_RFQ_template.xlsx')
            KITS_RFQ= st.download_button(label='📥 Download KITS RFQ template',
                                data=to_excel(KITS_RFQ_Template),
                                file_name= 'KITS_RFQ_Template.xlsx')
            file = st.file_uploader("Upload a Request For Quotation (following above template)")

            if file:
                RFQ=pd.read_excel(file)
                try:
                    valid_headers= (KITS_RFQ_Template.columns==RFQ.columns).min()
                except:
                    valid_headers= 0
                if not valid_headers :
                    st.write('Invalid file format: ')
                    for column in SHIMS_RFQ_Template.columns:
                        if column not in RFQ.columns:
                            st.write("'", column ,"' column is missing")
                elif valid_headers:
                    st.markdown("## RFQ Data loaded:")
                    st.dataframe(RFQ)

                    #FMSI matches
                    FMSI_matches= RFQ['D Plate Number'].str.extractall(r'(D\d+)')
                    FMSI_matches.rename({0: 'FMSI'}, axis= 1, inplace= True)
                    FMSI_matches.index.rename(['line', 'match'], inplace= True)
                    FMSI_matches['FMSI (short)']= FMSI_matches['FMSI'].apply(lambda s: re.sub(r'^D0*', 'D', s) )
                    st.markdown("## FMSI matches")
                    st.dataframe(FMSI_matches)

                    #RFQ Full match
                    st.markdown('## Full match:')
                   
                    SubResults= []
                    for line in FMSI_matches.index.get_level_values('line'):
                        line_results=[]
                        for match in FMSI_matches.loc[line, 'FMSI (short)']:
                            
                            temp_df= Flat_kits[(Flat_kits['FMSI (short)']==match)]
                            temp_df= Flat_kits[Flat_kits['FMSI (short)']==match]
                            line_results.append(set(temp_df["KIT PN"].values))
                        result= line_results[0].intersection(*line_results)
                        Result_df= Flat_kits.loc[(Flat_kits['KIT PN'].isin(result)) 
                                                    & (Flat_kits['FMSI (short)'].isin(FMSI_matches.loc[line, 'FMSI (short)']))]
                        Result_df['Line']= line
                        Result_df.set_index(['Line', 'KIT PN', 'FMSI (short)'], inplace= True)
                        SubResults.append(Result_df)
                        
                    Output= pd.concat(SubResults)
                    Output= Output.reset_index().drop_duplicates().set_index(['Line', 'KIT PN', 'FMSI (short)']).reset_index()

                    short_RFQ= RFQ.reset_index().rename(columns={"index":"Line"})[['Line', 'D Plate Number']].set_index("Line")
                    Output= Output.set_index('Line').join(short_RFQ).reset_index()

                    
                    Output['Cost']="$"
                    Output= Output[[
                        "Line",
                        "D Plate Number",
                        "FMSI (short)",
                        "FMSI",
                        "KIT PN",
                        "Cost",
                        "COO",
                        "FMSI 2",
                        "US CA UIO",
                        "US CA MX UIO",
                        "US 1 Year Grow Rate",
                        "Avg Age",
                        "Comment",
                        "Application(s)",
                        "COMMENT_x",
                        "CREATION DATE",
                        "LAST UPDATE",
                        "COMMENT_y",
                        "Comp. Part No",
                        "XLD Component - Qty",
                        "XLD Material Type",
                        "JMc Updated Xref - IBI",
                        "JMc Xref 2",
                        "Kit Contents - Qty and Description",
                        "Y/N",
                        "Verification",
                    ]]
                    st.dataframe(Output)
                    df_xlsx = to_excel(Output.reset_index())
                    st.download_button(label='📥 Download full match',
                                                    data=df_xlsx ,
                                                    file_name= 'RFQ_output.xlsx')
                    #Partial match
                    st.markdown('## Partial match:')
                    SubResults= []
                    for line in FMSI_matches.index.get_level_values('line'):
                        line_results=[]
                        for match in FMSI_matches.loc[line, 'FMSI (short)']:
                            
                            temp_df= Flat_kits[(Flat_kits['FMSI (short)']==match)]
                            temp_df= Flat_kits[Flat_kits['FMSI (short)']==match]
                            line_results.append(set(temp_df["KIT PN"].values))
                        result1= line_results[0].intersection(*line_results)
                        result2= line_results[0].union(*line_results)
                        result= result2.difference(result1)
                        Result_df= Flat_kits.loc[(Flat_kits['KIT PN'].isin(result)) 
                                                    & (Flat_kits['FMSI (short)'].isin(FMSI_matches.loc[line, 'FMSI (short)']))]
                        Result_df['Line']= line
                        Result_df.set_index(['Line', 'KIT PN', 'FMSI (short)'], inplace= True)
                        SubResults.append(Result_df)
                        
                        
                    Output_inc= pd.concat(SubResults)
                    Output_inc= Output_inc.reset_index().drop_duplicates().set_index(['Line', 'KIT PN', 'FMSI (short)']).reset_index()


                    #computing matching count (format: 3/7)
                    count_matches=Output_inc.reset_index()
                    count_matches=count_matches.groupby(['Line', 'KIT PN']).count()['FMSI (short)'].reset_index().set_index("Line")
                    count_per_line= FMSI_matches.reset_index().groupby('line').count()['match']

                    partial_match= count_matches.join(count_per_line, how='left')
                    partial_match['match count']= pd.DataFrame(partial_match['FMSI (short)'].apply(str)+"/"+partial_match['match'].apply(str))
                    partial_match=partial_match.reset_index().rename(columns={"index": "Line"})[['Line', 'KIT PN', 'match count']]
                    partial_match=partial_match.set_index(['Line', 'KIT PN'])

                    Output_inc= Output_inc.reset_index().set_index(['Line', 'KIT PN']).join(partial_match).reset_index()

                    short_RFQ= RFQ.reset_index().rename(columns={"index":"Line"})[['Line', 'D Plate Number']].set_index("Line")
                    Output_inc= Output_inc.set_index('Line').join(short_RFQ).reset_index()

                    
                    Output_inc['Cost']="$"
                    
                    Output_inc= Output_inc[[
                        "Line",
                        "D Plate Number",
                        "FMSI (short)",
                        "FMSI",
                        "KIT PN",
                        "Cost",
                        "COO",
                        "match count",
                        "FMSI 2",
                        "US CA UIO",
                        "US CA MX UIO",
                        "US 1 Year Grow Rate",
                        "Avg Age",
                        "Comment",
                        "Application(s)",
                        "COMMENT_x",
                        "CREATION DATE",
                        "LAST UPDATE",
                        "COMMENT_y",
                        "Comp. Part No",
                        "XLD Component - Qty",
                        "XLD Material Type",
                        "JMc Updated Xref - IBI",
                        "JMc Xref 2",
                        "Kit Contents - Qty and Description",
                        "Y/N",
                        "Verification",
                    ]]
                    st.dataframe(Output_inc)
                    

                    df_xlsx2 = to_excel(Output_inc.reset_index())
                    st.download_button(label='📥 Download partial match',
                                                    data=df_xlsx2 ,
                                                    file_name= 'RFQ_output_partial.xlsx')

                    
                    #No match
                    st.markdown('## No match:')
                    temp_Output= pd.concat([Output, Output_inc]).reset_index().set_index(['Line', 'FMSI (short)'])
                    temp_match= FMSI_matches.reset_index().set_index(['line', 'FMSI (short)'])
                    Output_index= temp_Output.index
                    Match_index= temp_match.index

                    key_diff = set(Match_index).difference(Output_index)
                    where_diff = temp_match.index.isin(key_diff)
                    Not_found= temp_match[where_diff].reset_index()

                    st.dataframe(Not_found)
                    df_xlsx3 = to_excel(Not_found.reset_index())
                    st.download_button(label='📥 Download no match',
                                                    data=df_xlsx2 ,
                                                    file_name= 'RFQ_output_no_match.xlsx')
    
      
        
        if page == "FMSI Lookup":
            FMSI= st.text_input(label= 'FMSI')
            FMSIs= FMSI.split(', ')
            FMSIs= [re.sub(r'^D0*', 'D', s) for s in FMSIs]
            result= Flat_kits[Flat_kits['FMSI (short)'].isin(FMSIs)]
            result= result.drop_duplicates().sort_values(['FMSI', "KIT PN"]).reset_index()
            result= result[[
                "FMSI",
                "FMSI (short)",
                "FMSI 2",
                "KIT PN",
                "US CA UIO",
                "US CA MX UIO",
                "US 1 Year Grow Rate",
                "Avg Age",
                "Comment",
                "Application(s)",
                "COMMENT_x",
                "CREATION DATE",
                "LAST UPDATE",
                "COMMENT_y",
                "Comp. Part No",
                "XLD Component - Qty",
                "XLD Material Type",
                "JMc Updated Xref - IBI",
                "JMc Xref 2",
                "Kit Contents - Qty and Description",
                "Y/N",
                "COO",
                "Verification"
            ]]
            st.dataframe(result)
            df_xlsx = to_excel(result.reset_index())
            st.download_button(label='📥 Download Lookup results',
                                            data=df_xlsx ,
                                            file_name= 'FMSI_Lookup_results.xlsx')
        if page == "KIT Lookup":
            KITs= st.text_input(label= 'KIT')
            KITs= KITs.split(', ')
            result= Flat_kits[Flat_kits['KIT PN'].isin(KITs)]
            result= result.drop_duplicates().sort_values(["KIT PN", 'FMSI']).reset_index()
            result= result[[
                "KIT PN",
                "FMSI",
                "FMSI (short)",
                "FMSI 2",
                "US CA UIO",
                "US CA MX UIO",
                "US 1 Year Grow Rate",
                "Avg Age",
                "Comment",
                "Application(s)",
                "COMMENT_x",
                "CREATION DATE",
                "LAST UPDATE",
                "COMMENT_y",
                "Comp. Part No",
                "XLD Component - Qty",
                "XLD Material Type",
                "JMc Updated Xref - IBI",
                "JMc Xref 2",
                "Kit Contents - Qty and Description",
                "Y/N",
                "COO",
                "Verification"
            ]]
            st.dataframe(result)

            df_xlsx = to_excel(result.reset_index())
            st.download_button(label='📥 Download Lookup results',
                                            data=df_xlsx ,
                                            file_name= 'KIT_Lookup_results.xlsx')

        if page == "KIT images":
                    
            list_images= os.listdir('Data/Images')
            img_dict={}
            for name in list_images:
                k= name[:-4]
                v=name
                img_dict[k]=v

            k= st.selectbox("Select an image",options= img_dict.keys())
            st.image(r"Data/Images/" + img_dict[k])

    if menu == "RAW DATA":
        Tables_dict= {"FMSI": FMSI, 
                      "SHIMS": SHIMS, 
                      "Kits": Kits, 
                      "Shim Crossing": Shim_crossing, 
                      "KIT Crossing": Kit_crossing}
        Table_name= st.radio("Pick a table", options= Tables_dict.keys(), horizontal=True)
        Table= Tables_dict[Table_name]
        st.dataframe(Table)

        df_xlsx = to_excel(Table.reset_index())
        st.download_button(label='''📥 Download "'''+Table_name+'''" table''',
                                        data=df_xlsx ,
                                        file_name= Table_name+'.xlsx')

