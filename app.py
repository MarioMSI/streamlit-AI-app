import streamlit as st
import ifcopenshell
import ifcopenshell.util.element
import pandas as pd
import tempfile

from langchain.agents.agent_types import AgentType
from langchain_experimental.agents.agent_toolkits import create_pandas_dataframe_agent
from langchain_openai import ChatOpenAI
#from langchain_groq import ChatGroq
from langchain_openai import OpenAI

#from langchain_community.callbacks import get_openai_callback

#* ----------------IFC TRANSFORMATION FUNCTIONS -------------------------------
def get_JSON_pset(list_GUID, file):
    # Diccionario para almacenar los JSON de Property Sets por list_
    pset_dict = {}  
    #Recorremos la lista de GUID que le hemos dado
    for guid in list_GUID:
        #Identifica el elemento que es en el ifc
        ifc_element = file.by_guid(guid)
        #Condicion para que ese elemento se encuentre
        if ifc_element is not None:
            #Extrae su pset en forma de diccionario
            pset_json = ifcopenshell.util.element.get_psets(ifc_element)
            #Añadimos al diccionario con la clave guid
            pset_dict[guid] = pset_json
        else:
            print("No se encontró el elemento con GUID:", guid)
    
    return pset_dict

def dict_a_df(result_dict):
    # Lista para almacenar filas del DataFrame
    filas = []
    for key, value in result_dict.items():
        fila = {"key": key}  # La primera columna es la key del diccionario
        if value:  # Verificar si el diccionario interno no está vacío
            for subkey, subdict in value.items():
                fila.update(subdict)
        filas.append(fila)  

    df_pset = pd.DataFrame(filas)
    return df_pset

def transform_ifc_to_df(file):
    #Extraemos todos los elementos del file
    elements = file.by_type('IfcRoot')

    #Creamos una lista vacia donde irán los GUID, name, type, predefined type
    list_GUID = []
    list_name = []
    list_type = []
    list_pretype = []
    #Recorremos todo el ifc
    for element in elements: 
        #extraemos ela info de cada elemento
        info = element.get_info()
        #Hacemos un append en cada lista de la información qe queremos
        list_GUID.append(info['GlobalId'])
        list_name.append(info['Name'])
        list_type.append(info['type'])
        try:
            list_pretype.append(info['PredefinedType'])
        except:
            list_pretype.append('None')

    #Hacemos un diccionario con los elementos 
    data = {
        'Guid' : list_GUID,
        'Name' : list_name,
        'IfcEntity' : list_type,
        'PredefinedType' : list_pretype
    }
    #Este df tiene todas las properties de los elementos
    df_properties = pd.DataFrame(data)

    #Este diccionario tiene los pset
    result_dict = get_JSON_pset(list_GUID, file)

    #Este df tiene los mismos elementos que el json
    df_pset = dict_a_df(result_dict)


    #este df tiene mergeadas las propiedades de los properties
    df_final_raw = pd.merge(df_pset, df_properties, how='left', left_on='key', right_on='Guid')

    #este df está filtrado por la columna 'Layer'. 
    df_final = df_final_raw[df_final_raw['Layer'].notna()]
    print('Las columnas que tendrá el df son: ')
    for i in df_final.columns:
        print(i)
    
    #Retornamos los dos df
    return df_final

#*-------------------------------APP----------------------------
with st.sidebar:
    open_api_key = st.text_input("Open AI API key", type='password')

# if not open_api_key:
#     st.warning("Please enter a valid Open AI API key.")
#     st.stop()
# st.session_state["api_key"] = open_api_key

st.title("Chat IFC")
st.write("""
         Upload your IFC and ask your model
         """)

uploaded_file = st.file_uploader("Upload file", type=(".ifc"))

st.write(" ## CHAT")
if uploaded_file:
    with tempfile.NamedTemporaryFile(delete=False, suffix=".ifc") as temp_file:
        temp_file.write(uploaded_file.getbuffer())
        temp_file_path = temp_file.name

    # Abrimos el archivo IFC utilizando ifcopenshell
    ifc_file = ifcopenshell.open(temp_file_path)

    df = transform_ifc_to_df(ifc_file)

    question = st.text_input(
        "Ask something about file",
        placeholder="Can you give me a short summary?",
        disabled=not uploaded_file,
    )

    if uploaded_file and question and not open_api_key:
        st.info('Please add OPEN_API_KEY')

    if uploaded_file and question and open_api_key:
        llm = ChatOpenAI(
            model="gpt-4o",
            temperature=0,
            stream_usage=True,
            api_key=open_api_key
            )

        agent = create_pandas_dataframe_agent(
            llm,
            df,
            verbose=True,
            agent_type=AgentType.OPENAI_FUNCTIONS,
            allow_dangerous_code=True
            )
        
        response = agent.invoke(question)
        st.write("### Answer")
        st.write(response['output'])



#! TODO
#"https://blog.streamlit.io/streamlit-authenticator-part-1-adding-an-authentication-component-to-your-app/"
# next step

