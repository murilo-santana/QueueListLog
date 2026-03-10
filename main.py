import asyncio
from playwright.async_api import async_playwright
from datetime import datetime, timedelta
import time
import os
import shutil
import gspread
import pandas as pd
from oauth2client.service_account import ServiceAccountCredentials

DOWNLOAD_DIR = "/tmp"

def rename_downloaded_file(download_dir, download_path):
    try:
        current_hour = datetime.now().strftime("%H")
        new_file_name = f"QUEUE-{current_hour}.csv"
        new_file_path = os.path.join(download_dir, new_file_name)
        if os.path.exists(new_file_path):
            os.remove(new_file_path)
        shutil.move(download_path, new_file_path)
        print(f"Arquivo salvo como: {new_file_path}")
        return new_file_path
    except Exception as e:
        print(f"Erro ao renomear o arquivo: {e}")
        return None

def update_packing_google_sheets(csv_file_path):
    try:
        if not os.path.exists(csv_file_path):
            print(f"Arquivo {csv_file_path} não encontrado.")
            return
        scope = ["https://www.googleapis.com/auth/spreadsheets", "https://www.googleapis.com/auth/drive"]
        creds = ServiceAccountCredentials.from_json_keyfile_name("hxh.json", scope)
        client = gspread.authorize(creds)
        sheet1 = client.open_by_url("https://docs.google.com/spreadsheets/d/1qvgVViwnLVkzLnjfWQLU3m6ce0f3lXrvg-aq2YF59v8")
        worksheet1 = sheet1.worksheet("queuelistlog")
        df = pd.read_csv(csv_file_path)
        df = df.fillna("")
        worksheet1.clear()
        worksheet1.update([df.columns.values.tolist()] + df.values.tolist())
        print(f"Arquivo enviado com sucesso para a aba 'PROD'.")
        time.sleep(5)
    except Exception as e:
        print(f"Erro durante o processo: {e}")

async def main():    
    os.makedirs(DOWNLOAD_DIR, exist_ok=True)
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=False, args=["--no-sandbox", "--disable-dev-shm-usage", "--window-size=1920,1080"])
        context = await browser.new_context(accept_downloads=True)
        page = await context.new_page()
        try:
            # LOGIN
            await page.goto("https://spx.shopee.com.br/")
            await page.wait_for_selector('xpath=//*[@placeholder="Ops ID"]', timeout=15000)
            await page.locator('xpath=//*[@placeholder="Ops ID"]').fill('Ops127185')
            await page.locator('xpath=//*[@placeholder="Senha"]').fill('@Shopee123')
            await page.locator('xpath=/html/body/div[1]/div/div[2]/div/div/div[1]/div[3]/form/div/div/button').click()
            await page.wait_for_timeout(10000)
            try:
                await page.locator('.ssc-dialog-close').click(timeout=5000)
            except:
                print("Nenhum pop-up foi encontrado.")
                await page.keyboard.press("Escape")

            # NAVEGAÇÃO E DOWNLOAD
            await page.goto("https://spx.shopee.com.br/#/queue-list")
            await page.wait_for_timeout(10000)
            await page.get_by_role("button", name="Log").click()
            # await page.locator('xpath=/html/body/div[1]/div/div[2]/div[2]/div/div/div/div/div/div[2]/div[2]/div[2]/div/div[2]/button[2]').click()
            await page.wait_for_timeout(10000)
            await page.locator('xpath=/html/body/div[1]/div/div[2]/div[2]/div/div/div/div/div/div[2]/button/span').click()
            await page.wait_for_timeout(10000)
            
            d3 = (datetime.now() - timedelta(days=3)).strftime("%Y/%m/%d")
            d1 = (datetime.now() + timedelta(days=1)).strftime("%Y/%m/%d")

            # Primeiro campo de data
            date_input = page.get_by_role("textbox", name="Data de início").nth(0)
            #date_input = page.locator('input[placeholder="Data de início"]').nth(0)
            #date_input = page.locator('xpath=/html[1]/body[1]/div[4]/div[2]/div[1]/div[1]/div[3]/div[2]/form[1]/div[1]/span[2]/div[1]/div[1]/span[1]/span[1]/input[1]').nth(0)
            await date_input.wait_for(state="visible", timeout=10000)
            await date_input.click(force=True)
            await date_input.fill(d3)

            # Segundo campo de data
            date_input = page.get_by_role("textbox", name="Data final").nth(0)
            #date_input = page.locator('input[placeholder="Data Final"]').nth(0)
            #date_input = page.locator('xpath=/html[1]/body[1]/div[4]/div[2]/div[1]/div[1]/div[3]/div[2]/form[1]/div[1]/span[2]/div[1]/div[1]/span[3]/span[1]/input[1]').nth(0)
            await date_input.wait_for(state="visible", timeout=10000)
            await date_input.click(force=True)
            await date_input.fill(d1)
            await page.wait_for_timeout(5000)
            
            #await page.getByText('Exportar').nth(1).click()
            #await page.get_by_role("text", name="Exportar").nth(1).click()
            #await page.locator('xpath=/html/body/div[4]/div[2]/div/div/div[3]/div[2]/form/div/span[1]').click()
            await page.get_by_role('button', name='Confirmar').click()
            await page.wait_for_timeout(5000)
            await page.get_by_role('button', name='Confirm').click()
            await page.wait_for_timeout(10000)

          
# 👉 Botão de download
            async with page.expect_download() as download_info:
                await page.get_by_role("button", name="Baixar").nth(0).click()
                #await page.locator('xpath=/html/body/span/div/div[1]/div/span/div/div[2]/div[2]/div[1]/div/div[1]/div/div[1]/div[2]/button').click()
            download = await download_info.value
            download_path = os.path.join(DOWNLOAD_DIR, download.suggested_filename)
            await download.save_as(download_path)
            new_file_path = rename_downloaded_file(DOWNLOAD_DIR, download_path)
            

            # Atualizar Google Sheets (opcional)
            if new_file_path:
                update_packing_google_sheets(new_file_path)
                print("Dados atualizados com sucesso.")
        except Exception as e:
            print(f"Erro durante o processo: {e}")
        finally:
            await browser.close()

if __name__ == "__main__":
    asyncio.run(main())
