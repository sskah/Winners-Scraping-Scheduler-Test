import time
import pandas as pd
from bs4 import BeautifulSoup
from selenium import webdriver
from selenium.webdriver.chrome.options import Options
import json
import os
import math

options = Options()
options.add_argument('--headless') 
options.add_argument('--disable-gpu')
options.add_argument('--no-sandbox')

driver = webdriver.Chrome(options=options)

BASE_URL = "https://www.lovethework.com/work-awards/results?festival_name=Cannes+Lions"
print("Acessando página principal...")
driver.get(BASE_URL)
time.sleep(10)

soup = BeautifulSoup(driver.page_source, 'html.parser')
containers = soup.find_all('div', {'type': 'Container'})
category_links = []

print("Buscando links das categorias...")
for container in containers:
    category_blocks = container.find_all('div', id=True)
    for block in category_blocks:
        table = block.find('table')
        if not table:
            continue
        rows = table.find_all('tr')
        for row in rows:
            link_td = row.find('td', {'type': 'link'})
            if link_td and link_td.find('a'):
                href = link_td.find('a').get('href')
                full_url = f"https://www.lovethework.com{href}"
                category_links.append(full_url)

total_categories = len(category_links)
print(f"{total_categories} categorias encontradas.")

# Carrega dados existentes para evitar duplicatas
excel_path = 'cannes_lions_winners.xlsx'
if os.path.exists(excel_path):
    print("Carregando dados existentes da planilha para evitar duplicatas...")
    existing_df = pd.read_excel(excel_path)
    existing_links = set(existing_df['Shortlist'].dropna().astype(str).tolist())
else:
    existing_df = pd.DataFrame()
    existing_links = set()

print("Buscando vencedores divulgados...")

all_rows = []
next_progress = 10  # próxima % para printar
for idx, link in enumerate(category_links, 1):
    perc = (idx / total_categories) * 100
    if perc >= next_progress:
        print(f"Progresso: {next_progress:.0f}%")
        next_progress += 10

    try:
        driver.get(link)
        time.sleep(4)
        soup = BeautifulSoup(driver.page_source, 'html.parser')

        button = None
        tags_with_text = soup.find_all(string=lambda text: text and "Results Table" in text)
        for text_tag in tags_with_text:
            parent_a = text_tag.find_parent('a')
            if parent_a and parent_a.get('href'):
                button = parent_a
                break

        results_url = f"https://www.lovethework.com{button.get('href')}"
        driver.get(results_url)
        time.sleep(4)

        soup = BeautifulSoup(driver.page_source, 'html.parser')
        result_sections = soup.find_all('div', {'id': True})

        for section in result_sections:
            subcategory = section.find('h2').get_text(strip=True) if section.find('h2') else "N/A"
            table = section.find('table')
            if not table:
                continue

            headers = []
            thead = table.find('thead')
            if thead:
                headers = [th.get_text(strip=True) for th in thead.find_all('td')]

            tbody = table.find('tbody')
            if not tbody:
                continue

            rows = tbody.find_all('tr')
            for row in rows:
                values = []
                row_link = ''

                cells = row.find_all('td')
                for cell in cells:
                    if cell.get('type') == 'link':
                        p_tag = cell.find('p')
                        cell_text = p_tag.get_text(strip=True) if p_tag else ''
                        values.append(cell_text)

                        a_tag = cell.find('a')
                        if a_tag and a_tag.get('href'):
                            row_link = f"https://www.lovethework.com{a_tag.get('href')}"
                    else:
                        values.append(cell.get_text(strip=True))

                if row_link in existing_links:
                    continue

                row_dict = {'Subcategoria': subcategory}
                if headers and len(headers) == len(values):
                    row_dict.update(dict(zip(headers, values)))
                else:
                    for i, val in enumerate(values):
                        row_dict[f'Coluna_{i+1}'] = val

                row_dict['Shortlist'] = row_link
                row_dict['Case'] = row_link
                all_rows.append(row_dict)
                existing_links.add(row_link)

    except Exception as e:
        print(f"Erro ao processar {link}: {e}")

if next_progress <= 100:
    print("Progresso: 100%")

if not all_rows:
    print("Ainda nao foram divulgados novos vencedores.")
    final_df = existing_df
else:
    print(f"Adicionando {len(all_rows)} novos vencedores à planilha.")
    new_df = pd.DataFrame(all_rows)
    final_df = pd.concat([existing_df, new_df], ignore_index=True)

final_df.to_excel(excel_path, sheet_name='WINNERS', index=False)

driver.quit()
print(f"Execução concluída. Planilha atualizada: '{excel_path}'")