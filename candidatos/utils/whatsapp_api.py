# utils/whatsapp_api.py

import requests
from django.conf import settings

def enviar_mensaje_whatsapp(destinatario_telefono, mensaje):
    """
    Función para enviar un mensaje de texto simple usando la Meta Cloud API.
    
    Args:
        destinatario_telefono (str): Número con código de país (ej. 51999888777).
        mensaje (str): Contenido del mensaje de texto.
    
    Returns:
        dict: Diccionario con 'success' (bool) y el detalle de la respuesta/error.
    """
    
    url = f"{settings.WHATSAPP_API_URL}{settings.WHATSAPP_PHONE_ID}/messages"
    
    headers = {
        "Authorization": f"Bearer {settings.WHATSAPP_ACCESS_TOKEN}",
        "Content-Type": "application/json"
    }
    
    payload = {
        "messaging_product": "whatsapp",
        "to": destinatario_telefono,
        "type": "text",
        "text": {
            "body": mensaje
        }
    }
    
    try:
        response = requests.post(url, headers=headers, json=payload)
        response.raise_for_status() 
        
        return {
            'success': True, 
            'data': response.json()
        }
    
    except requests.exceptions.HTTPError as err:
        print(f"Error HTTP de la API de WhatsApp: {err}")
        return {
            'success': False, 
            'message': f"API Error: {response.text}"
        }
    except Exception as e:
        print(f"Error general al enviar mensaje: {e}")
        return {
            'success': False, 
            'message': f"Error de conexión: {e}"
        }