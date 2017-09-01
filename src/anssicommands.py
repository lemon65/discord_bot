# Anssi's first command!!
import time
import random
import asyncio

default_choices =["Kyllä", "Ei", "Ehkä" , "Hmm.." , "Mjaa.." , "En osaa vastata tuohon"]
is_choices =["On", "Ei ole" , "Ehkä" , "Kyllä varmaan" , "Ei varmaan" , "Todellakin" , "Ei todellakaan"]
from_choices =["Pyllystä", "Sun mutsista", "Sossusta", "Kaupasta", "No vittu just sieltä", "Säkylästä" , "Stadista" , "Ei mistään"]
when_choices =["Viimeksi joulukuussa" , "Ei vittu ikinä" , "Aikavälillä 10,000ekr - 2068" , "Vuonna 85"]
why_choices =["Koska säkylän pystykorvat" , "Kukaan ei tiedä" , "Se on jumalan suunnitelma" , "Tuntemattomista syistä"]
where_choices =["Helvetin perseessä" , "Jumalan selän takana" , "Nyrkki perseessä säkylässä" , "Leppävaarassa"]
who_choices =["Helvetin perkeleet" , "Niske" , "Henry" , "Chimppa" , "Tuntematon mieshenkilö" , "Anps" , "Tommi" , "En tiedä"]
how_choices =["Katso googlesta" , "En tiedä enkä osaa" , "En voi auttaa asian kanssa" , "Hääv juu traid rebooting?" , "Kynsisaksilla"]
what_choices =["Kasa paskaa" , "Kuuku vitun pööpötin" , "Puhdas ja sileä honkanen" , "Reaktorin tesla" , "Anime"]
whatlike_choices =["Ruosteinen" , "Paskainen" , "Jostain syystä pahanhajuinen" , "Jännä" , "Pullea" , "Söpö"]
areyou_choices =["Kyllä olen", "En voi kertoa" , "En" , "Se on salaisuus"]
arewe_choices =["Olette" , "Ette ole" , "En voi kertoa" , "Se on salaisuus"]
arethey_choices =["Ovat" , "Ei ole" , "En kerro"]
worldDomination_choices =["En kerro" , "Huomenna tai ylihuomenna" , "16.09.2028" , "23.04.2026" , "Viikon sisällä" , "Tänään"]
rain_choices =["Sataa ihan vitusti" , "Ei mutta paskaa tulee taivaalta" , "Joo, voi tulla vettä niskaan" , "Ei sada"]
weather_choices =["En osaa ennustaa" , "Puolipilvistä" , "Epämääräinen" , "Kertakaikkiaan ihan vitun paska keli" , "Lol ihanku menisit ulos"]
should_choices =["Kyllä" , "Ei" , "Ei ikinä" , "Tottakai"]

async def cmd_ask(client, message, question):
    if not question:
        await client.send_message(message.channel, 'kys pls')
        return

    if question.lower().startswith("onko"):
        choices = is_choices
    elif question.lower().startswith("mistä"):
        choices = from_choices
    elif question.lower().startswith("milloin") or question.lower().startswith("millon"):
        choices = when_choices
    elif question.lower().startswith("miksi") or question.lower().startswith("minkä takia"):
        choices = why_choices
    elif question.lower().startswith("missä"):
        choices = where_choices
    elif question.lower().startswith("kuka"):
        choices = who_choices
    elif question.lower().startswith("miten") or question.lower().startswith("kuinka"):
        choices = how_choices
    elif question.lower().startswith("mikä"):
        choices = what_choices
    elif question.lower().startswith("millainen") or question.lower().startswith("minkälainen"):
        choices = whatlike_choices
    elif question.lower().startswith("oletko") or question.lower().startswith("ookko"):
        choices = areyou_choices
    elif question.lower().startswith("olemmeko"): 
        choices = arewe_choices               
    elif question.lower().startswith("ovatko"):                    
        choices = arethey_choices                
    elif question.lower().startswith("maailmanvalloitus"):
        choices = worldDomination_choices
    elif question.lower().startswith("sataako"):                    
        choices = rain_choices                
    elif question.lower().startswith("sää"):
        choices = weather_choices
    elif question.lower().startswith("pitäisikö") or question.lower().startswith("pitäiskö"):
        choices = should_choices       
    else:
        choices = default_choices

    await asyncio.sleep(2)
    await client.send_message(message.channel, random.choice(choices) + " :thinking: ")

def register(client):
    return {
        'ask': cmd_ask
    }
