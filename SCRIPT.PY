import re
import os
import json
import OpenSSL
from OpenSSL import crypto
from google.oauth2.service_account import Credentials
from googleapiclient.discovery import build

# Caminho para o arquivo JSON de credenciais
SERVICE_ACCOUNT_FILE = 'Credentials.json'  # Substitua pelo caminho real

# ID da planilha (encontre isso na URL da sua planilha Google)
# Substitua pelo ID real da sua planilha
SPREADSHEET_ID = '1cFOFfLFiTpWx6JWqktXTUjUhHGv0uv24dX-PdFfOcI8'

# Nome da aba
SHEET_NAME = 'DadosCertificados'

# Autenticação e criação do serviço Google Sheets


def authenticate_google_sheets():
    credentials = Credentials.from_service_account_file(
        SERVICE_ACCOUNT_FILE,
        scopes=["https://www.googleapis.com/auth/spreadsheets"]
    )
    service = build('sheets', 'v4', credentials=credentials)
    return service

# Função para extrair informações de certificados


def get_certificate_info():
    command = 'certutil -store -user My'
    output = os.popen(command).read()

    certificates = []
    current_cert = {}
    in_cert = False
    issuer = None

    print("Saída do certutil:")
    print(output)

    for line in output.splitlines():
        print(f"Processando linha: {line}")  # Diagnóstico

        if line.startswith('================'):
            if in_cert and current_cert:
                if all(key in current_cert for key in ['CNPJ/CPF', 'RAZÃO SOCIAL', 'VALIDADE', 'EMISSOR']):
                    certificates.append(current_cert)
                else:
                    print(f"Certificado incompleto ou inválido: {
                          current_cert}")
                current_cert = {}
            in_cert = not in_cert
        elif in_cert:
            if 'Emissor:' in line:
                issuer = line.split('Emissor:')[1].strip()
                current_cert['EMISSOR'] = issuer
            elif 'Requerente:' in line:
                try:
                    req_line = line.split('Requerente:')[1].strip()
                    req_parts = req_line.split(', ')

                    cnpj_part = [part for part in req_parts if ':' in part]
                    if cnpj_part:
                        current_cert['CNPJ/CPF'] = cnpj_part[0].split(':')[
                            1].strip()

                    name_part = [part for part in req_parts if 'CN=' in part]
                    if name_part:
                        current_cert['RAZÃO SOCIAL'] = name_part[0].split('CN=')[
                            1].strip()

                except IndexError as e:
                    print(f"Erro ao processar a linha: {line}. Erro: {e}")
            elif 'NotAfter:' in line:
                current_cert['VALIDADE'] = line.split(':', 1)[1].strip()

    if in_cert and current_cert:
        if all(key in current_cert for key in ['CNPJ/CPF', 'RAZÃO SOCIAL', 'VALIDADE', 'EMISSOR']):
            certificates.append(current_cert)
        else:
            print(f"Certificado incompleto ou inválido: {current_cert}")

    print("Dados dos certificados:")
    for cert in certificates:
        print(cert)

    return certificates


# Chame a função para testar
certificates = get_certificate_info()
print(f"Número total de certificados encontrados: {len(certificates)}")


# Função para enviar dados para o Google Sheets


def update_google_sheet(service, data):
    sheet = service.spreadsheets()
    # Converte os dados para o formato necessário
    values = [['CNPJ/CPF', 'RAZÃO SOCIAL', 'VALIDADE']] + [
        [cert['CNPJ/CPF'], cert['RAZÃO SOCIAL'], cert['VALIDADE']] for cert in data
    ]

    body = {
        'values': values
    }

    # Imprima os dados para verificar o formato
    print("Dados a serem enviados para o Google Sheets:")
    for row in body['values']:
        print(row)

    # Atualiza a planilha com os novos dados
    result = sheet.values().update(
        spreadsheetId=SPREADSHEET_ID,
        range=f"{SHEET_NAME}!A1",
        valueInputOption="RAW",
        body=body
    ).execute()

    print(f"{result.get('updatedCells')} células atualizadas.")


def main():
    service = authenticate_google_sheets()
    cert_data = get_certificate_info()
    update_google_sheet(service, cert_data)


if __name__ == '__main__':
    main()
