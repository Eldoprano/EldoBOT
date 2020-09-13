from bs4 import BeautifulSoup
import requests

loli_detected = False
page = requests.get("https://nhentai.net/g/251863/")
soup = BeautifulSoup(page.content, 'html.parser')

tags = soup.find(id="tags")
for tag_type in list(tags.children):
    if(tag_type.contents[0].lower().find("tags")!=-1):
        for tag in tag_type.findAll("span", class_='name'):
            if(tag.getText().lower().find("lolicon")!=-1):
                loli_detected = True

