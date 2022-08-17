import discord, asyncio, os, random, requests, dropbox
from discord.ext.commands.core import cooldown
from dotenv import load_dotenv
from datetime import datetime
from discord.utils import get
from discord.ext import commands
from discord import Embed
from discord_components import Button, Select, SelectOption, ComponentsBot, component
from os import path
from PIL import Image
import numpy as np
import pyshorteners as sh

class globales:
    prefix = "--"
    admin = "admin"
    adminId = 0
    categoryName = "synthese"
    offCategoryName = "cimetiere"
    gameOn = False

with open("data") as file:
    for line in file:
        match line.split(':')[0].strip():
            case "prefix":
                globales.prefix = line.split(':')[1].strip()
            case "admin":
                globales.admin = line.split(':')[1].strip()
            case "adminId":
                globales.adminId = int(line.split(':')[1].strip())
            case "categoryName":
                globales.categoryName = line.split(':')[1].strip()
            case "gameOn":
                match line.split(':')[1].strip():
                    case "True":
                        globales.gameOn = True
                    case "False":
                        globales.gameOn = False
            case "offCategoryName":
                globales.offCategoryName = line.split(':')[1].strip()

#asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())
load_dotenv(dotenv_path="token")
#bot = commands.Bot(command_prefix="--")
bot = ComponentsBot(globales.prefix)
bot.remove_command('help')

dbx = dropbox.Dropbox(os.getenv("DROPBOX_TOKEN"))

##################### EVENTS #####################
class events():
    lastGiverToday = "Noboy"
    lastGiverScore = 0

    highScoreName = "Noboy"
    highScore = 0

    @bot.event
    async def on_ready():
        await appelable.update_highscore()
        print("Le bot est prêt")
        choice = 0
        while True:
            if(globales.gameOn):
                await appelable.actu_game()
            await appelable.update_data()
            match choice:
                case 0:
                    await bot.change_presence(activity=discord.Game("Prefix: %s | %shelp" % (globales.prefix, globales.prefix)))
                case 1:
                    await bot.change_presence(activity=discord.Game("👉%s | %d👈" % (events.lastGiverToday, events.lastGiverScore)))
                case 2:
                    await appelable.update_highscore()
                    await bot.change_presence(activity=discord.Game("👑%s | %d👑" % (events.highScoreName, events.highScore)))
            choice += 1
            choice = choice % 3
            await asyncio.sleep(random.randint(20, 60))


    @bot.event
    async def on_guild_join(guild):
        if guild.system_channel: # If it is not None
            await guild.system_channel.send("Merci de l'invitation sur !\nJe te conseille de faire la commande %ssetup" % globales.prefix)

##################### COMMANDS #####################
class commands():
    @bot.command(name='gettime')
    async def gettime(ctx):
        await ctx.message.delete()
        now = datetime.now()
        current_time = now.strftime("%H:%M")
        await ctx.send("Il est actuellement %s" % current_time)

    @bot.command(name='synthese')
    async def synthese(ctx):
        await ctx.message.delete()
        guild = ctx.message.guild
        author = ctx.message.author
        category = get(ctx.guild.categories, name=globales.categoryName)#Recupere la categorie dans laquelle viendront les channels
        adminWait = False 
        moreFile = True
        embed = Embed(title="Veux-tu envoyer un autre fichier ?",color=0x00ffff)
        embedClose = Embed(title="Clique si tu souhaites fermer le salon",color=0x00ffff)

        overwrites = {
        guild.default_role: discord.PermissionOverwrite(read_messages=False),
        guild.me: discord.PermissionOverwrite(read_messages=True),
        author: discord.PermissionOverwrite(read_messages=True, send_messages=True)
        }
        channel = await guild.create_text_channel('🟢 synthese %s' % ctx.author.display_name , overwrites=overwrites, category=category) #Cree un channel dans la bonne categorie
        
        while moreFile:
            await asyncio.sleep(3)
            synthese = await appelable.geresynthese(channel)
            if(synthese[0] == 0 ):
                await channel.edit(name='🟡 synthese %s' % ctx.author.display_name )

                msg = await bot.wait_for('message', timeout= 60)
                await asyncio.sleep(3)
                attachment_url = msg.attachments[0].url
                attachment_name = msg.attachments[0].filename

                #METTRE ICI LE PATH COMPLET
                if(int(synthese[2]) < 4):
                    pathh = "dowld_files/B%s/%s/%s/%s/%s" % (synthese[2], synthese[3], synthese[6], synthese[4], synthese[5])
                else:
                    pathh = "dowld_files/M%s/%s/%s/%s/%s" % (synthese[2], synthese[3], synthese[6], synthese[4], synthese[5])

                if(path.exists(pathh) == False):
                    os.makedirs(pathh)
                else:
                    print("Il existe déjà le dossier %s" % pathh)


                with open("%s/%s" % (pathh, attachment_name), 'wb') as f:
                    f.write(requests.get(attachment_url).content)
                    
                score = (await appelable.calc_score_file(msg) + synthese[1])//100
                events.lastGiverToday = ctx.author.display_name
                events.lastGiverScore = score

                await appelable.save_score_in_file(score, ctx)

                #AJOUTER ICI LA FONCTION D'AJOUT AUTO SUR LE CLOUD
                await appelable.upload_dropbox(attachment_name, pathh)

                await asyncio.sleep(4)
                os.remove("%s/%s" % (pathh, attachment_name)) #Permet d'enlever le fichier du dossier local après téléchargement
                #await msg.delete() #Supp le message de la synthese

                now = datetime.now()
                current_time_days = now.strftime(f"%d/%m/%Y")
                current_time_hour = now.strftime(f"%H:%M:%S")
                out = open("logs.csv", 'a')
                out.writelines("%d;%s;%s;%s;%s;%d;%s;%s;%s;%s;%s\n" % (ctx.message.author.id, current_time_days, current_time_hour, ctx.message.author.name, attachment_name, score, synthese[2], synthese[3], synthese[4], synthese[5], synthese[6]))
                out.close()

                #Demander si on veut reupload un truc
                selectBtn = await channel.send(embed = embed, components=[Select(placeholder="Répond moi...",options=[SelectOption(label="Oui", value="Y"),SelectOption(label="Non", value="N"),],custom_id="select5",)],)
                interaction = await bot.wait_for("select_option", check=lambda inter: inter.custom_id == "select5")
                match interaction.values[0]:
                    case "Y":
                        moreFile = True
                    case "N":
                        moreFile = False
                await interaction.defer(edit_origin=True)
                await selectBtn.delete()
            else:
                selectBtn = await channel.send(embed = embed, components=[Select(placeholder="Répond moi...",options=[SelectOption(label="Oui", value="Y"),SelectOption(label="Non", value="N"),],custom_id="select1",)],)
                interaction = await bot.wait_for("select_option", check=lambda inter: inter.custom_id == "select1")
                match interaction.values[0]:
                    case "Y":
                        moreFile = True
                    case "N":
                        moreFile = False
                await interaction.defer(edit_origin=True)
                await selectBtn.delete()
                adminWait = True
        
        
        if(adminWait):
            await channel.edit(name="🟣 synthese %s || En attente d'admin" % ctx.author.display_name )
            selectBtn = await channel.send(embed = embedClose, components=[[Button(emoji="❌", custom_id="button3", style=1)]])
            interaction = await bot.wait_for("button_click")
            await interaction.defer(edit_origin=True)
            if(interaction.custom_id == "button3"):
                await channel.edit(name="🔴 synthese %s" % ctx.author.display_name, category=globales.offCategoryName)
                await channel.set_permissions(author, overwrite=discord.PermissionOverwrite(read_messages=False, send_messages=False))
                await selectBtn.delete()


        if(adminWait == False):
            await channel.edit(name="🔴 synthese %s || Score: %d" % (ctx.author.display_name, score))
            await channel.set_permissions(author, overwrite=discord.PermissionOverwrite(read_messages=False, send_messages=False))

    @bot.command(name='search')
    async def search_synth(ctx):
        await ctx.message.delete()
        
        embed1 = Embed(title="Choisi un dossier")
        buttons = []
        originPath = "/dowld_files"
        annee = ""
        fac = ""
        idCours = ""
        YorN = ""

        response = dbx.files_list_folder(originPath)
        for i in range(0, len(response.entries)):
            buttons.append(Button(label=response.entries[i].name, custom_id=response.entries[i].name))
        bts = [buttons]
        embeded = await ctx.send(embed = embed1, components=bts)
        interaction = await bot.wait_for("button_click", check=lambda inter: inter.author.id == ctx.author.id)
        await interaction.defer(edit_origin=True)

        for i in range(1,5):
            match i:
                case 1:
                    annee = interaction.custom_id
                    originPath = "/dowld_files/%s" % annee
                case 2:
                    fac = interaction.custom_id
                    originPath = "/dowld_files/%s/%s" % (annee, fac)
                case 3:
                    idCours = interaction.custom_id
                    originPath = "/dowld_files/%s/%s/%s" % (annee, fac, idCours)
                case 4:
                    YorN = interaction.custom_id
                    originPath = "/dowld_files/%s/%s/%s/%s" % (annee, fac, idCours, YorN)
            response = dbx.files_list_folder(originPath)
            buttons = []
            for i in range(0, len(response.entries)):
                buttons.append(Button(label=response.entries[i].name, custom_id=response.entries[i].name))
            bts = [buttons]
            await embeded.edit(components=bts)
            interaction = await bot.wait_for("button_click", check=lambda inter: inter.author.id == ctx.author.id)
            await interaction.defer(edit_origin=True)

        result = dbx.files_get_temporary_link("/dowld_files/%s/%s/%s/%s/%s" % (annee, fac, idCours, YorN, interaction.custom_id))
        link = result.link
        s = sh.Shortener()
        tinyDownldUrl = s.tinyurl.short(link)
        embedLink = Embed(title = "Lien du fichier",description = "%s" % tinyDownldUrl)
        buttons = []

        for i in range(10, 0, -1):
            embedLink = Embed(title = "Lien du fichier | %d" % i,description = "%s" % tinyDownldUrl)
            await embeded.edit(embed = embedLink, components = buttons)
            await asyncio.sleep(1)
        await embeded.delete()

    @bot.command('link')
    async def cloud_link(ctx):
        await ctx.message.delete()
        result = dbx.sharing_create_shared_link("/dowld_files")
        link = result.url
        s = sh.Shortener()
        tinyDownldUrl = s.tinyurl.short(link)
        embedLink = Embed(title = "Lien du cloud",description = "%s" % tinyDownldUrl)
        embeded = await ctx.send(embed = embedLink)
        for i in range(10, 0, -1):
            embedLink = Embed(title = "Lien du cloud | %d" % i,description = "%s" % tinyDownldUrl)
            await embeded.edit(embed = embedLink)
            await asyncio.sleep(1)
        await embeded.delete()

    @bot.command(name='getscore')
    async def get_score(ctx):
        await ctx.message.delete()
        filename = "scoreList"
        id = ctx.message.author.id
        with open(filename) as file:
            for line in file:
                if(int(float(line.split(':')[0].strip())) == id):
                    embed = Embed(title="Ton score est: %s" % int(float(line.split(':')[1].strip())), color=0x00ff00)
                    embed.set_author(name=ctx.author.display_name, icon_url=ctx.author.avatar_url)
                    await ctx.send(embed = embed)
        file.close()
            
    @bot.command(name='help')
    async def help(ctx):
        await ctx.message.delete()
        buttons = [[Button(emoji="❌", custom_id="button3", style=1), Button(emoji="👉🏽", custom_id="button1", style=1)]]
        buttons2 = [[Button(emoji="❌", custom_id="button3", style=1), Button(emoji="👈🏽", custom_id="button2", style=1)]]

        embed = Embed(title="__**Help**__", description="__Page 1:__",color=0x00ffff)
        embed.add_field(name="**%sgettime**" % globales.prefix, value="Permet d'obtenir l'heure actuelle", inline=False)
        embed.add_field(name="**%ssynthese**" % globales.prefix, value="Crée un salon ou tu pourras envoyer ta synthèse", inline=False)
        embed.add_field(name="**%sgetscore**" % globales.prefix, value="Permet d'obtenir ton score global", inline=False)
        embed.add_field(name="**%ssearch**" % globales.prefix, value="Permet de rechercher un fichier dans le cloud", inline=False)
        embed.add_field(name="**%slink**" % globales.prefix, value="Permet d'avoir le lien du cloud", inline=False)

        embedP2 = Embed(title="__**Help**__", description="__Page 2:__", color=0x00ffff)
        embedP2.add_field(name="**%sprefix [prefix]**" % globales.prefix, value="Permet de changer le prefix des commandes du bot avec le [prefix]\n**Il faut être admin pour exécuter cette commande**", inline=False)
        embedP2.add_field(name="**%sgivescore [x]**" % globales.prefix, value="Permet d'ajouter [x] a ton score\n**Il faut être admin pour exécuter cette commande**", inline=False)
        embedP2.add_field(name="**%ssetup**" % globales.prefix, value="Permet de configurer le bot sur le serveur\n**Il faut être admin pour exécuter cette commande**", inline=False)
        embedP2.add_field(name="**%savatar [url image]**" % globales.prefix, value="Permet de changer l'avatar du bot\n**Il faut être admin pour exécuter cette commande**", inline=False)

        embedFerm = [Embed(title="Fermeture de l'aide", color=0x00ffff), Embed(title="Fermeture de l'aide.", color=0x00ffff), Embed(title="Fermeture de l'aide..", color=0x00ffff), Embed(title="Fermeture de l'aide...", color=0x00ffff)]

        embeded = await ctx.send(embed=embed, components=buttons)

        loop = True
        while loop:
            interaction = await bot.wait_for("button_click")
            await interaction.defer(edit_origin=True)
            if(interaction.custom_id == "button1"):
                await embeded.edit(embed=embedP2, components=buttons2)
            if(interaction.custom_id == "button2"):
                await embeded.edit(embed=embed, components=buttons)
            if(interaction.custom_id == "button3"):
                loop = False
                for x in range(4):
                    await embeded.edit(embed=embedFerm[x])
                    await asyncio.sleep(1)

        await embeded.delete()
        return 0

    @bot.command(name='givescore')
    async def give_score(ctx, arg):
        await ctx.message.delete()
        role = discord.utils.get(ctx.guild.roles, id=globales.adminId)
        if role in ctx.message.author.roles:
            i = 0
            ici = -1
            filename = "scoreList"
            name = ctx.message.author.name
            id = ctx.message.author.id
            with open(filename) as file:
                for line in file:
                    i += 1
                    if(int(float(line.split(':')[0].strip())) == id):
                        score = int(line.split(':')[1].strip()) + int(float(arg))
                        ici = i
                        await appelable.replace_line(filename, ici-1, '%s:%d:%s\n'%(id, score, name))
            file.close()
        else:
            await ctx.send("Tu n'as pas ma permission de faire cette commande", delete_after = 2)
        return 0

    @bot.command()
    async def narno(ctx):
        await ctx.message.delete()
        road = ["⬜️⬛️⬛️⬜️⬛️⬛️⬜️⬜️⬛️⬛️⬜️⬜️⬜️⬛️⬛️⬜️⬛️⬛️⬜️⬛️⬛️⬜️⬜️⬛️⬛️",
                "⬜️⬛️⬛️⬜️⬛️⬜️⬛️⬛️⬜️⬛️⬜️⬛️⬛️⬜️⬛️⬜️⬛️⬛️⬜️⬛️⬜️⬛️⬛️⬜️⬛️",
                "⬜️⬜️⬛️⬜️⬛️⬜️⬜️⬜️⬜️⬛️⬜️⬜️⬜️⬛️⬛️⬜️⬜️⬛️⬜️⬛️⬜️⬛️⬛️⬜️⬛️",
                "⬜️⬛️⬜️⬜️⬛️⬜️⬛️⬛️⬜️⬛️⬜️⬛️⬜️⬛️⬛️⬜️⬛️⬜️⬜️⬛️⬜️⬛️⬛️⬜️⬛️",
                "⬜️⬛️⬛️⬜️⬛️⬜️⬛️⬛️⬜️⬛️⬜️⬛️⬛️⬜️⬛️⬜️⬛️⬛️⬜️⬛️⬛️⬜️⬜️⬛️⬛️"]
        emnarno = Embed(description=road[0] + road[1]+ road[2] + road[3] + road[4])
        await ctx.send(embed = emnarno)
        return 0

    @bot.command()
    async def takit(ctx):
        await ctx.message.delete()
        head = 12
        apple = random.randint(0,20)

        line = 5
        row = 5
        score = 0
        level = 0
        levelPalier = [20, 100, 200, 500, 1000, 5000]
        levelMax = 6
        playing = True

        buttons = [[Button(label="Gauche", custom_id="left"), Button(label="Haut", custom_id="up"), Button(label="Droite", custom_id="right")], [Button(label="Quitter", custom_id="quit"), Button(label="Bas", custom_id="down")]]

        allTab = ""

        for x in range(row*line):
            if(x%line == 0):
                allTab = allTab + "\n"
            if x == head:
                allTab = allTab + "⬜️"
            elif x == apple:
                allTab = allTab + "🔴"
            else:
                allTab = allTab + "⬛️"

        emSnek = Embed(title="TakIt | Score : %d" % score, description=allTab)

        embeded = await ctx.send(embed = emSnek, components=buttons)
        

        while playing:
            try:
                interaction = await bot.wait_for("button_click", check=lambda inter: inter.author.id == ctx.author.id)
                await interaction.defer(edit_origin=True)
                match interaction.custom_id:
                    case "up":
                        if(head - row > 0):
                            head = head - row
                        else:
                            head = head + ((line*row)-line)
                    case "down":
                        if(head + line < row*line):
                            head = head + row
                        else:
                            head = head - ((line*row)-line)
                    case "left":
                        if(head%row == 0):
                            head = head + (line-1)
                        else:
                            head = head - 1
                    case "right":
                        if((head+1)%row == 0):
                            head = head - (line-1)
                        else:
                            head = head + 1
                    case "quit":
                        for i in range(5, 0, -1):
                            emSnek = Embed(title="Fin TakIt | Score : %d | %d" % (score, i))
                            await embeded.edit(embed=emSnek)
                            await asyncio.sleep(1)
                        playing = False
                        await embeded.delete()

                if(head == apple):
                    score += 10
                    apple = random.randint(0,(line*row)-line)

                ancienLevel = level
                for x in range(levelMax):
                    if score == levelPalier[x]:
                        level = x + 1
                if(ancienLevel < level):
                    line += 1
                    row += 1
                        
                allTab = ""
                for x in range(row*line):
                    if(x%line == 0):
                        allTab = allTab + "\n"
                    if x == head:
                        allTab = allTab + "⬜️"
                    elif x == apple:
                        allTab = allTab + "🔴"
                    else:
                        allTab = allTab + "⬛️"
            except:
                print("Nope")

            if(interaction.custom_id != "quit"):
                emSnek = Embed(title="TakIt | Score : %d | Lvl: %d" % (score, level), description=allTab)
                await embeded.edit(embed=emSnek)

        return 0

    @bot.command(name="prefix")
    async def change_prefix(ctx, pref):
        await ctx.message.delete()
        role = discord.utils.get(ctx.guild.roles, id=globales.adminId)
        if role in ctx.message.author.roles:
            bot.command_prefix = pref
            globales.prefix = pref
            await ctx.send("Prefix mit sur: %s" % pref, delete_after = 5)
            await appelable.update_data()
        else:
            await ctx.send("Tu n'as pas ma permission de faire cette commande", delete_after = 2)
        return 0

    @bot.command(name='setup')#A FAIRE: ECRIRE DANS UN FICHIER CAR SINON A CHAQUE FOIS QUE ON RALLUME LE BOT LES GLOBALES SE RESET ET FAUT REFAIRE UN SETUP
    async def setup_all(ctx):
        await ctx.message.delete()
        role = discord.utils.get(ctx.guild.roles, id=globales.adminId)
        embed0 = Embed(title="Commencement du setup", color=0x00ff00)
        embed1 = Embed(title="Comment nommes-tu la catégorie des synthèses ?\nSi elle est déja crée, écrit son nom.", color=0x00ff00)
        embed5 = Embed(title="Comment nommes-tu la catégorie des logs?\nSi elle est déja crée, écrit son nom.", color=0x00ff00)
        embed2 = Embed(title="Quel est le rôle d'administrateur (Mentionne-le)", color=0x00ff00)
        embed4 = Embed(title="Que veux-tu comme préfixe pour les commandes du bot ?", color=0x00ff00)
        embed3 = Embed(title="Setup fini !", color=0x00ff00)
        if role in ctx.message.author.roles:
            try:
                embeded = await ctx.send(embed=embed0)
                await asyncio.sleep(2)
                await embeded.edit(embed=embed1)
                msg = await bot.wait_for('message', check=lambda message: message.author == ctx.author)
                await ctx.send("Tu as choisi le nom: %s" % msg.content, delete_after=1)
                globales.categoryName = msg.content
                if(await appelable.category_exist(ctx, globales.categoryName) == 0):#VERIF SI LA CATEGORIE EXISTE PO DEJA
                    category = await ctx.guild.create_category(globales.categoryName, overwrites=None, reason=None)
                await asyncio.sleep(2)
                await msg.delete()

                await embeded.edit(embed=embed1)
                msg = await bot.wait_for('message', check=lambda message: message.author == ctx.author)
                await ctx.send("Tu as choisi le nom: %s" % msg.content, delete_after=1)
                globales.offCategoryName = msg.content
                if(await appelable.category_exist(ctx, globales.offCategoryName) == 0):#VERIF SI LA CATEGORIE EXISTE PO DEJA
                    category = await ctx.guild.create_category(globales.offCategoryName, overwrites=None, reason=None)
                await asyncio.sleep(2)
                await msg.delete()

                await embeded.edit(embed=embed2)
                msg = await bot.wait_for('message', check=lambda message: message.author == ctx.author)
                await ctx.send("Tu as choisi le rôle: %s" % msg.content, delete_after=1)
                globales.admin = msg.content
                roleid = msg.content.replace("<@&","")
                globales.admin = roleid.replace(">","")
                await asyncio.sleep(2)
                await msg.delete()

                await embeded.edit(embed=embed4)
                msg = await bot.wait_for('message', check=lambda message: message.author == ctx.author)
                await ctx.send("Tu as choisi le préfixe: %s" % msg.content, delete_after=1)
                globales.prefix = msg.content
                await asyncio.sleep(2)
                await msg.delete()

                await embeded.edit(embed=embed3)
                await asyncio.sleep(3)
                await embeded.delete()
                await appelable.update_data()
            except Exception as errors:
                print(f"Bot Error: {errors}")
        else:
            await ctx.send("Tu n'as pas ma permission de faire cette commande", delete_after = 2)

    @bot.command(name='oeuvre')
    async def random_img(ctx, name):
        await ctx.message.delete()
        width = random.randint(500, 1500)
        height = random.randint(500, 1500)

        array = np.random.random_integers(0,255, (height,width,3))  

        array = np.array(array, dtype=np.uint8)
        img = Image.fromarray(array)
        img.save("oeuvres/%s.png" % name)
        await ctx.send(file=discord.File("oeuvres/%s.png" % name))
        

    @bot.command(name='avatar')
    async def change_bot_avatar(ctx, url):
        await ctx.message.delete()
        try:
            role = discord.utils.get(ctx.guild.roles, id=globales.adminId)
            if role in ctx.message.author.roles:
                with open("%s/%s" % ("dowld_files/", "avatar_bot.png"), 'wb') as f:
                        f.write(requests.get(url).content)
                with open("dowld_files/avatar_bot.png", 'rb') as image:
                    await bot.user.edit(avatar=image.read())
            else:
                await ctx.send("Tu n'as pas ma permission de faire cette commande", delete_after = 2)
        except:
            await ctx.send("Vérifie bien que ton lien donne accès à une image PNG !")

    @bot.command(name='pixels')
    async def change_pixels_actu(ctx, height, width, color):
        await ctx.message.delete()
        if(int(height) < 1000 and int(width) < 1000 and int(height) > 0 and int(width) > 0):
            im = Image.open("serverGame.png")
            pixels = im.load()
            match color:
                case "rouge":
                    idColor = (255, 0, 0)
                case "bleu":
                    idColor = (0, 0, 255)
                case "vert":
                    idColor = (0, 255, 0)
            pixels[int(height), int(width)] = idColor
            im.save("serverGame.png")
            #print("Height: %d Width: %d Color: %s" % (int(height), int(width), idColor))
        else:
            ctx.send("Ton x et y doit être compris entre 0 et 1000")
        return 0

    @bot.command(name='gameMode')
    async def change_game_statut(ctx):
        await ctx.message.delete()
        match globales.gameOn:
            case False:
                if(await appelable.category_exist(ctx, "Jeu") == 0):#VERIF SI LA CATEGORIE EXISTE PO DEJA
                    category = await ctx.guild.create_category("Jeu", overwrites=None, reason=None)
                    await ctx.guild.create_text_channel('Actualisation', overwrites=None, category=category)
                globales.gameOn = True
                #await appelable.actu_game()
                await ctx.send("Mode de jeu mit sur on", delete_after=2)
            case True:
                globales.gameOn = False
                await ctx.send("Mode de jeu mit sur off", delete_after=2)
        await appelable.update_data()

    @bot.command(name='resetGame')
    async def reset_game(ctx):
        await ctx.message.delete()
        array = np.random.random_integers(255,255, (1000,1000,3))  
        array = np.array(array, dtype=np.uint8)
        img = Image.fromarray(array)
        img.save("serverGame.png")


##################### FONCTION APPELABLE #####################
class appelable():
    async def geresynthese(channel):
        synthese = [0, 0, 0, 0, 0, 0, 0] #[return, score]
        tab = []
        faculte = ""
        annee = ""
        fileType = ""
        idCours = ""
        ecrite = ""
        embed0 = Embed(title="La taille de la synthèse est-elle inférieur à 8 MB?", color=0x00ff00)
        embed1 = Embed(title="Dans quelle fac etes vous?", color=0x00ff00)
        embed2 = Embed(title="En quelle année etes vous?", color=0x00ff00)
        embed3 = Embed(title="Quel est l'id cours concerné?", color=0x00ff00)
        embed4 = Embed(title="Votre synthese est-elle écrite a l'ordinateur?", color=0x00ff00)
        embed5 = Embed(title="Il ne vous reste plus qu'a uploader votre synthese ici", color=0x00ff00)
        embed6 = Embed(title="Merci champion(ne)!!", color=0x00ff00)
        embed7 = Embed(title="Quel type de fichier veux-tu envoyer ?", color=0x00ff00)
        embedError = Embed(title="Il fallait répondre plus vite ou mieux !", color=0xff0000)
        embedNo = Embed(title="Nos admins sont sur le coup, patiente le temps qu'il arrive", color=0xff0000)
        listeAnnee = [SelectOption(label="B1", value="1"),SelectOption(label="B2", value="2"),SelectOption(label="B3", value="3"),SelectOption(label="M1", value="4"),SelectOption(label="M2", value="5"),]
        listeCoursInfoId = [SelectOption(label="INFO0030", value="INFO0030"),SelectOption(label="INFO0946", value="INFO0946"),SelectOption(label="MATH0025", value="MATH0025"),]
        listeCoursIngeId = [SelectOption(label="INGE0040", value="INGE0040"),SelectOption(label="INGE3345", value="INGE3345"),SelectOption(label="ANGL3348", value="ANGL3348"),]

        selectBtn = await channel.send(embed = embed0, components=[Select(placeholder="Répond moi...",options=[SelectOption(label="Oui", value="Y"),SelectOption(label="Non", value="N"),SelectOption(label="Non mais j'ai discord Nitro", value="I"),],custom_id="select1",)],)
        try:
            interaction = await bot.wait_for("select_option", check=lambda inter: inter.custom_id == "select1")
            await interaction.defer(edit_origin=True)


            match interaction.values[0]:
                case "N":
                    embeded = await channel.send(embed = embedNo)
                    await selectBtn.delete()
                    synthese[1] = 0
                    synthese[0] = 1
                case ("Y"|"I"):
                    await selectBtn.edit(embed=embed1, components=[Select(placeholder="Facultés",options=[SelectOption(label="Info", value="INFO"),SelectOption(label="Inge", value="INGE"),],custom_id="select1",)],)
                    interaction = await bot.wait_for("select_option", check=lambda inter: inter.custom_id == "select1")
                    faculte = interaction.values[0]
                    await interaction.defer(edit_origin=True)

                    await selectBtn.edit(embed=embed2, components=[Select(placeholder="Années",options=listeAnnee,custom_id="select1",)],)
                    interaction = await bot.wait_for("select_option", check=lambda inter: inter.custom_id == "select1")
                    annee = interaction.values[0]
                    await interaction.defer(edit_origin=True)

                    await selectBtn.edit(embed=embed7, components=[Select(placeholder="Type de fichier",options=[SelectOption(label="Synthèse", value="SYNTH"),SelectOption(label="Exercices", value="EXOS"),SelectOption(label="Autre", value="DIVERS"),],custom_id="select1",)],)
                    interaction = await bot.wait_for("select_option", check=lambda inter: inter.custom_id == "select1")
                    fileType = interaction.values[0]
                    await interaction.defer(edit_origin=True)

                    if(faculte == "INFO"):
                        await selectBtn.edit(embed=embed3, components=[Select(placeholder="Cours",options=listeCoursInfoId,custom_id="select1",)],)
                    elif(faculte == "INGE"):
                        await selectBtn.edit(embed=embed3, components=[Select(placeholder="Cours",options=listeCoursIngeId,custom_id="select1",)],)
                    interaction = await bot.wait_for("select_option", check=lambda inter: inter.custom_id == "select1")
                    idCours = interaction.values[0]
                    await interaction.defer(edit_origin=True)

                    await selectBtn.edit(embed=embed4, components=[Select(placeholder="Répond moi...",options=[SelectOption(label="Oui", value="Y"),SelectOption(label="Non", value="N"),],custom_id="select1",)],)
                    interaction = await bot.wait_for("select_option", check=lambda inter: inter.custom_id == "select1")
                    ecrite = interaction.values[0]
                    await interaction.defer(edit_origin=True)

                    await selectBtn.delete()

                    embeded = await channel.send(embed = embed5)
                    await asyncio.sleep(2)
                    await embeded.edit(embed=embed6) ##Embed 6
                    match ecrite:
                        case "Y":
                            embed7 = Embed(title="Tu es dans la fac %s en %s, l'id du cours est %s et ta synthèse est écrite à l'ordinateur" % (faculte, annee, idCours), color=0x00ff00)
                        case "N":
                            embed7 = Embed(title="Tu es dans la fac %s en %s, l'id du cours est %s et ta synthèse n'est pas écrite à l'ordinateur" % (faculte, annee, idCours), color=0x00ff00)
                    await asyncio.sleep(1)
                    await embeded.edit(embed=embed7) ##Embed 7

                    tab = [faculte, annee, idCours, ecrite]
                    synthese[6] = fileType
                    synthese[5] = ecrite
                    synthese[4] = idCours
                    synthese[3] = faculte
                    synthese[2] = annee
                    synthese[1] = await appelable.calc_score(tab)        
                    synthese[0] = 0
                    if(random.randint(0,25000) == 256):
                        await channel.Send("Wow tu as pas mal de chance toi !\nTu viens de débloquer un ptit truc bien sympa !", delete_after=2)
                        await asyncio.sleep(3)
                        commands.takit(channel)
        except:
            await selectBtn.edit(embed=embedError, components=[Select(placeholder="ERROR",options=[SelectOption(label="ERROR", value="E"),],custom_id="select1",)],)
            await interaction.defer(edit_origin=True)
            synthese[1] = 0
            synthese[0] = 1
        return synthese

    async def calc_score_file(file):
        data = file.attachments[0]
        score = data.size*2 

        if(data.height != None and data.width != None):
            score = score + data.height + data.width 
        return score

    async def calc_score(tab):
        score =  0
        if(tab[0] == "INFO"):
            score += 25000
        else:
            score += 12000
        score = score * int(tab[1])/2
        if(tab[0] == "Y"):
            score = score * (8**2/48)
        return score

    async def save_score_in_file(score, ctx):
        i = 0
        ici = -1
        filename = "scoreList"
        name = ctx.message.author.name
        id = ctx.message.author.id
        with open(filename) as file:
            for line in file:
                i += 1
                if(float(int(line.split(':')[0].strip())) == id):
                    score = int(line.split(':')[1].strip()) + score
                    ici = i
                    await appelable.replace_line(filename, ici-1, '%s:%d:%s\n'%(id, score, name))
        file.close()

        if(ici == -1):
            await appelable.add_line(filename, id, score, name)

        return 0

    async def replace_line(file_name, line_num, text):
        lines = open(file_name, 'r').readlines()
        lines[line_num] = text
        out = open(file_name, 'w')
        out.writelines(lines)
        out.close()

    async def add_line(file_name, id, score, name):
        out = open(file_name, 'a')
        out.writelines("\n%s:%d:%s" % (id, score, name))
        out.close()

    async def update_highscore():
        with open("scoreList") as file:
            for line in file:
                if(events.highScore < int(float(line.split(':')[1].strip()))):
                    events.highScore = int(float(line.split(':')[1].strip()))
                    events.highScoreName = line.split(':')[2].strip()
        file.close()

    async def upload_dropbox(filename, pathh):
        pathWithFile = "%s/%s" % (pathh, filename)

        with open(pathWithFile, 'rb') as f:
            data = f.read()

        try: 
            dbx.files_upload(data, "/%s" % pathWithFile)
        except:
            print("Impossible d'upload le fichier %s" % filename)

        return 0

    async def category_exist(ctx, categoryName):
        category = get(ctx.guild.categories, name=categoryName)
        if(category == None):
            return 0
        else:
            return 1

    async def actu_game():
        channel = discord.utils.get(bot.get_all_channels(), name="actualisation")
        await channel.purge(limit=2)
        await channel.send(file=discord.File("serverGame.png"))

    async def update_data():
        filename = "data"
        await appelable.replace_line(filename, 0, 'prefix:%s\n' % globales.prefix)
        await appelable.replace_line(filename, 1, 'admin:%s\n' % globales.admin)
        await appelable.replace_line(filename, 2, 'adminId:%d\n' % globales.adminId)
        await appelable.replace_line(filename, 3, 'categoryName:%s\n' % globales.categoryName)
        match globales.gameOn:
                        case True:
                            await appelable.replace_line(filename, 4, 'gameOn:True\n')
                        case False:
                            await appelable.replace_line(filename, 4, 'gameOn:False\n')
        await appelable.replace_line(filename, 5, 'offCategoryName:%s\n' % globales.offCategoryName)

bot.run(os.getenv("TOKEN"))
