import discord
from discord.ext import commands
from discord import ButtonStyle, ui
import aiohttp
import asyncio
import json
import re
from datetime import datetime
import uuid as uuid_lib

# إعدادات البوت
intents = discord.Intents.default()
intents.message_content = True
bot = commands.Bot(command_prefix="!", intents=intents)

# ملفات البيانات
DATA_FILE = "players.json"
LOG_FILE = "log.json"
NAME_HISTORY_FILE = "name_history.json"

def load_data():
    """تحميل بيانات اللاعبين"""
    try:
        with open(DATA_FILE, "r", encoding='utf-8') as f:
            return json.load(f)
    except:
        return {}

def save_data(data):
    """حفظ بيانات اللاعبين"""
    try:
        with open(DATA_FILE, "w", encoding='utf-8') as f:
            json.dump(data, f, separators=(',', ':'), ensure_ascii=False)
    except Exception as e:
        print(f"❌ خطأ في حفظ البيانات: {e}")

def load_log():
    """تحميل سجل التغييرات"""
    try:
        with open(LOG_FILE, "r", encoding='utf-8') as f:
            return json.load(f)
    except:
        return []

def save_log(log_data):
    """حفظ سجل التغييرات"""
    try:
        with open(LOG_FILE, "w", encoding='utf-8') as f:
            json.dump(log_data, f, separators=(',', ':'), ensure_ascii=False)
    except Exception as e:
        print(f"❌ خطأ في حفظ السجل: {e}")

def load_name_history():
    """تحميل تاريخ الأسماء"""
    try:
        with open(NAME_HISTORY_FILE, "r", encoding='utf-8') as f:
            return json.load(f)
    except:
        return {}

def save_name_history(history_data):
    """حفظ تاريخ الأسماء"""
    try:
        with open(NAME_HISTORY_FILE, "w", encoding='utf-8') as f:
            json.dump(history_data, f, separators=(',', ':'), ensure_ascii=False)
    except Exception as e:
        print(f"❌ خطأ في حفظ تاريخ الأسماء: {e}")

def add_log_entry(action, user, target, details=""):
    """إضافة مدخل للسجل"""
    log_data = load_log()
    
    log_entry = {
        "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        "action": action,
        "user": user,
        "target": target,
        "details": details
    }
    
    log_data.append(log_entry)
    
    # الحفاظ على السجل محدود الحجم
    if len(log_data) > 1000:
        log_data = log_data[-1000:]
    
    save_log(log_data)

def add_name_history(uuid, old_name, new_name):
    """إضافة تغيير اسم للمحفوظات"""
    history_data = load_name_history()
    
    if uuid not in history_data:
        history_data[uuid] = []
    
    name_change = {
        "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        "old_name": old_name,
        "new_name": new_name
    }
    
    history_data[uuid].append(name_change)
    
    # الحفاظ على آخر 20 تغيير فقط
    if len(history_data[uuid]) > 20:
        history_data[uuid] = history_data[uuid][-20:]
    
    save_name_history(history_data)


class PaginationView(ui.View):
    """مشاهد للتنقل بين الصفحات مع تحسينات"""
    def __init__(self, embeds, timeout=120, show_extreme_buttons=False):
        super().__init__(timeout=timeout)
        self.embeds = embeds
        self.current_page = 0
        self.show_extreme_buttons = show_extreme_buttons
        
        # إزالة الأزرار الموجودة أولاً
        self.clear_items()
        
        # إضافة الأزرار بناءً على الإعدادات
        if self.show_extreme_buttons:
            self.add_item(self.first_button)
        
        self.add_item(self.previous_button)
        self.add_item(self.page_label)
        self.add_item(self.next_button)
        
        if self.show_extreme_buttons:
            self.add_item(self.last_button)
        
        self.update_buttons()
    
    def update_buttons(self):
        """تحديث حالة الأزرار"""
        self.previous_button.disabled = self.current_page == 0
        self.next_button.disabled = self.current_page == len(self.embeds) - 1
        
        if self.show_extreme_buttons:
            self.first_button.disabled = self.current_page == 0
            self.last_button.disabled = self.current_page == len(self.embeds) - 1
        
        # تحديث التسمية
        if len(self.embeds) > 1:
            self.page_label.label = f"الصفحة {self.current_page + 1}/{len(self.embeds)}"
        else:
            self.page_label.label = "الصفحة 1/1"
    
    @ui.button(emoji="⏪", style=ButtonStyle.green, row=0)
    async def first_button(self, interaction: discord.Interaction, button: ui.Button):
        if self.current_page > 0:
            self.current_page = 0
            self.update_buttons()
            await interaction.response.edit_message(embed=self.embeds[self.current_page], view=self)
    
    @ui.button(emoji="⬅️", style=ButtonStyle.gray, row=0)
    async def previous_button(self, interaction: discord.Interaction, button: ui.Button):
        if self.current_page > 0:
            self.current_page -= 1
            self.update_buttons()
            await interaction.response.edit_message(embed=self.embeds[self.current_page], view=self)
    
    @ui.button(label="الصفحة 1/1", style=ButtonStyle.blurple, row=0, disabled=True)
    async def page_label(self, interaction: discord.Interaction, button: ui.Button):
        pass
    
    @ui.button(emoji="➡️", style=ButtonStyle.gray, row=0)
    async def next_button(self, interaction: discord.Interaction, button: ui.Button):
        if self.current_page < len(self.embeds) - 1:
            self.current_page += 1
            self.update_buttons()
            await interaction.response.edit_message(embed=self.embeds[self.current_page], view=self)
    
    @ui.button(emoji="⏩", style=ButtonStyle.green, row=0)
    async def last_button(self, interaction: discord.Interaction, button: ui.Button):
        if self.current_page < len(self.embeds) - 1:
            self.current_page = len(self.embeds) - 1
            self.update_buttons()
            await interaction.response.edit_message(embed=self.embeds[self.current_page], view=self)

def create_paginated_embeds(items, title, items_per_page=20, color=discord.Color.blue()):
    """إنشاء إيمبدز مقسمة إلى صفحات"""
    pages = []
    
    for i in range(0, len(items), items_per_page):
        page_items = items[i:i + items_per_page]
        description = "\n".join(page_items)
        
        embed = discord.Embed(
            title=f"{title} (الصفحة {i//items_per_page + 1}/{(len(items) + items_per_page - 1)//items_per_page})",
            description=description,
            color=color
        )
        
        # إضافة تذييل بالمعلومات
        embed.set_footer(text=f"إجمالي العناصر: {len(items)}")
        
        pages.append(embed)
    
    return pages

async def get_uuid_from_username(username):
    """جلب UUID من اسم اللاعب"""
    try:
        url = f"https://api.mojang.com/users/profiles/minecraft/{username}"
        async with aiohttp.ClientSession() as session:
            async with session.get(url, timeout=10) as response:
                if response.status == 200:
                    data = await response.json()
                    return data["id"], data["name"]
                return None, None
    except Exception as e:
        print(f"❌ خطأ في جلب UUID لـ {username}: {e}")
        return None, None

async def get_username_from_uuid(uuid):
    """جلب الاسم الحالي من UUID"""
    try:
        url = f"https://sessionserver.mojang.com/session/minecraft/profile/{uuid}"
        async with aiohttp.ClientSession() as session:
            async with session.get(url, timeout=10) as response:
                if response.status == 200:
                    data = await response.json()
                    return data["name"]
                return None
    except Exception as e:
        print(f"❌ خطأ في جلب الاسم لـ {uuid}: {e}")
        return None

def is_valid_uuid(uuid):
    """التحقق من صحة UUID"""
    uuid_pattern = re.compile(r'^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$', re.I)
    return bool(uuid_pattern.match(uuid))

@bot.event
async def on_ready():
    print(f"✅ تم تسجيل الدخول كـ {bot.user}")

@bot.event
async def on_message(message):
    if message.author == bot.user:
        return
    await bot.process_commands(message)

@bot.command()
async def addplayer(ctx, *, identifier):
    """إضافة لاعب باستخدام الاسم أو UUID مباشرة"""
    
    data = load_data()
    
    # التحقق إذا كان UUID مباشرة
    if is_valid_uuid(identifier):
        uuid = identifier
        current_name = await get_username_from_uuid(uuid)
        
        if not current_name:
            await ctx.send(f"❌ UUID غير صالح أو اللاعب غير موجود: `{identifier}`")
            return
            
        if uuid in data:
            # 🔥 إذا اللاعب موجود، تحقق إذا الاسم تغير
            stored_name = data[uuid]
            if stored_name != current_name:
                # الاسم تغير، قم بتحديثه
                old_name = stored_name
                data[uuid] = current_name
                save_data(data)
                add_name_history(uuid, old_name, current_name)
                add_log_entry("NAME_UPDATE", str(ctx.author), f"{old_name} → {current_name}", f"UUID: {uuid}")
                
                embed = discord.Embed(
                    title="🔄 تم تحديث الاسم",
                    description=f"✅ اللاعب موجود وكان اسمه: `{old_name}`\n🔄 تم تحديثه إلى: `{current_name}`",
                    color=discord.Color.orange()
                )
            else:
                # نفس الاسم
                await ctx.send(f"⚠️ اللاعب **{current_name}** موجود بالفعل في القائمة")
                return
        else:
            # إضافة جديدة
            data[uuid] = current_name
            save_data(data)
            add_log_entry("ADD_UUID", str(ctx.author), current_name, f"UUID: {uuid}")
            
            embed = discord.Embed(
                title="✅ تم إضافة اللاعب",
                description=f"**الاسم:** {current_name}\n**UUID:** `{uuid}`",
                color=discord.Color.green()
            )
        await ctx.send(embed=embed)
        return
    
    # إذا كان اسم لاعب (وليس UUID)
    uuid, current_name = await get_uuid_from_username(identifier)
    
    if not uuid:
        await ctx.send(f"❌ اللاعب غير موجود: **{identifier}**")
        return
    
    if uuid in data:
        # 🔥 إذا اللاعب موجود، تحقق إذا الاسم تغير
        stored_name = data[uuid]
        if stored_name != current_name:
            # الاسم تغير، قم بتحديثه
            old_name = stored_name
            data[uuid] = current_name
            save_data(data)
            add_name_history(uuid, old_name, current_name)
            add_log_entry("NAME_UPDATE", str(ctx.author), f"{old_name} → {current_name}", f"UUID: {uuid}")
            
            embed = discord.Embed(
                title="🔄 تم تحديث الاسم",
                description=f"✅ اللاعب موجود وكان اسمه: `{old_name}`\n🔄 تم تحديثه إلى: `{current_name}`",
                color=discord.Color.orange()
            )
        else:
            # نفس الاسم
            await ctx.send(f"⚠️ اللاعب **{current_name}** موجود بالفعل في القائمة")
            return
    else:
        # إضافة جديدة
        data[uuid] = current_name
        save_data(data)
        add_log_entry("ADD", str(ctx.author), current_name, f"UUID: {uuid}")
        
        embed = discord.Embed(
            title="✅ تم إضافة اللاعب",
            description=f"**الاسم:** {current_name}\n**UUID:** `{uuid}`",
            color=discord.Color.green()
        )
    
    await ctx.send(embed=embed)

@bot.command()
async def addplayers(ctx, *, usernames):
    """إضافة عدة لاعبين مرة واحدة"""
    
    names = re.split(r'[\s,;]+', usernames.strip())
    names = [n for n in names if n]
    
    if len(names) > 100:
        await ctx.send("❌ الحد الأقصى 100 لاعب في المرة الواحدة")
        return
    
    loading_msg = await ctx.send(f"🔄 جاري معالجة {len(names)} لاعب...")
    
    data = load_data()
    added = []
    updated = []  # 🔥 جديدة: للتحديثات
    failed = []
    already_exists = []

    for i, username in enumerate(names):
        # تأخير بين الطلبات
        if i > 0:
            await asyncio.sleep(0.4)
        
        try:
            uuid, current_name = await get_uuid_from_username(username)
            
            if uuid:
                if uuid in data:
                    # 🔥 تحقق إذا الاسم تغير
                    stored_name = data[uuid]
                    if stored_name != current_name:
                        # تحديث الاسم
                        data[uuid] = current_name
                        add_name_history(uuid, stored_name, current_name)
                        add_log_entry("NAME_UPDATE", str(ctx.author), f"{stored_name} → {current_name}", f"UUID: {uuid}")
                        updated.append(f"{stored_name} → {current_name}")
                    else:
                        # نفس الاسم
                        already_exists.append(username)
                else:
                    # إضافة جديدة
                    data[uuid] = current_name or username
                    added.append(current_name or username)
                    add_log_entry("ADD", str(ctx.author), current_name or username, f"UUID: {uuid}")
            else:
                failed.append(username)
                
        except Exception as e:
            print(f"❌ خطأ في معالجة {username}: {e}")
            failed.append(username)
    
    save_data(data)
    
    desc = ""
    if added:
        desc += f"✅ **تمت إضافة:** {', '.join(added)}\n"
    if updated:
        desc += f"🔄 **تم تحديث:** {', '.join(updated)}\n"
    if already_exists:
        desc += f"⚠️ **موجود مسبقاً:** {', '.join(already_exists)}\n"
    if failed:
        desc += f"❌ **فشل إضافة:** {', '.join(failed)}"

    embed = discord.Embed(
        title="📥 نتيجة المعالجة",
        description=desc or "لم يتم معالجة أي لاعب",
        color=discord.Color.green() if added or updated else discord.Color.orange()
    )
    
    await loading_msg.edit(content="", embed=embed)


@bot.command()
async def playerlist(ctx):
    """عرض قائمة اللاعبين مع تقسيم إلى صفحات"""
    
    data = load_data()
    
    if not data:
        await ctx.send("📭 القائمة فارغة")
        return
    
    updated_list = []
    name_changes = []

    for uuid, stored_name in data.items():
        try:
            current_name = await get_username_from_uuid(uuid)
            
            if current_name and current_name != stored_name:
                name_changes.append(f"`{stored_name}` → `{current_name}`")
                data[uuid] = current_name
                add_name_history(uuid, stored_name, current_name)
                add_log_entry("NAME_CHANGE", "SYSTEM", f"{stored_name} → {current_name}", f"UUID: {uuid}")
                updated_list.append(f"• {current_name}")
            elif current_name:
                updated_list.append(f"• {current_name}")
            else:
                updated_list.append(f"• ❓ {stored_name}")
                
        except Exception as e:
            print(f"❌ خطأ في تحديث {stored_name}: {e}")
            updated_list.append(f"• ❓ {stored_name}")
    
    if name_changes:
        save_data(data)
    
    # 🔥 عرض التغييرات أولاً
    if name_changes:
        if len(name_changes) <= 30:
            changes_text = "\n".join(name_changes)
            changes_embed = discord.Embed(
                title="🔄 تغييرات الأسماء",
                description=changes_text,
                color=discord.Color.orange()
            )
            await ctx.send(embed=changes_embed)
        else:
            changes_pages = create_paginated_embeds(
                name_changes,
                "🔄 تغييرات الأسماء",
                items_per_page=25,
                color=discord.Color.orange()
            )
            
            if len(changes_pages) == 1:
                await ctx.send(embed=changes_pages[0])
            else:
                view = PaginationView(changes_pages)
                await ctx.send(embed=changes_pages[0], view=view)
    
    # 🔥 عرض القائمة الرئيسية مع التقسيم
    if len(updated_list) <= 30:
        players_text = "\n".join(updated_list)
        embed = discord.Embed(
            title=f"📋 قائمة اللاعبين - {len(updated_list)} لاعب",
            description=players_text,
            color=discord.Color.blue()
        )
        await ctx.send(embed=embed)
    else:
        list_pages = create_paginated_embeds(
            updated_list,
            f"📋 قائمة اللاعبين ({len(updated_list)})",
            items_per_page=25,
            color=discord.Color.blue()
        )
        
        view = PaginationView(list_pages)
        await ctx.send(embed=list_pages[0], view=view)

@bot.command()
async def checknames(ctx):
    """فحص وتحديث الأسماء مع تقسيم النتائج"""
    
    data = load_data()
    
    if not data:
        await ctx.send("📭 القائمة فارغة")
        return
    
    total_players = len(data)
    initial_msg = await ctx.send("🚀 **بدء فحص الأسماء**\n" + "⬜" * 20 + f" 0% (0/{total_players})")
    
    name_changes = []
    no_changes = []
    failed_updates = []

    players_list = list(data.items())
    progress_interval = max(1, total_players // 20)
    
    for i, (uuid, stored_name) in enumerate(players_list):
        if i > 0:
            await asyncio.sleep(0.4)
        
        try:
            current_name = await get_username_from_uuid(uuid)
            
            if current_name and current_name != stored_name:
                name_changes.append(f"• `{stored_name}` → `{current_name}`")
                data[uuid] = current_name
                add_name_history(uuid, stored_name, current_name)
                add_log_entry("NAME_CHANGE", "SYSTEM", f"{stored_name} → {current_name}", f"UUID: {uuid}")
            elif current_name:
                no_changes.append(stored_name)
            else:
                failed_updates.append(stored_name)
                
        except Exception as e:
            print(f"❌ خطأ في فحص {stored_name}: {e}")
            failed_updates.append(stored_name)
        
        if (i + 1) % progress_interval == 0 or (i + 1) == total_players:
            percentage = ((i + 1) / total_players) * 100
            filled = int(percentage / 5)
            progress_bar = "🟩" * filled + "⬜" * (20 - filled)
            
            await initial_msg.edit(
                content=f"🚀 **جاري فحص الأسماء**\n{progress_bar} {percentage:.1f}% ({i+1}/{total_players})"
            )
    
    if name_changes:
        save_data(data)
    
    # تغيير رسالة التحميل للنتيجة
    result_bar = "🟩" * 20
    await initial_msg.edit(
        content=f"✅ **اكتمل الفحص**\n{result_bar} 100% ({total_players}/{total_players})"
    )
    
    # إرسال التقرير الرئيسي
    embed = discord.Embed(
        title="📊 تقرير فحص الأسماء",
        color=discord.Color.green() if not name_changes else discord.Color.orange()
    )
    
    embed.add_field(
        name="📈 الإحصائيات",
        value=f"• **الإجمالي:** {total_players} لاعب\n"
              f"• **🔄 تم التغيير:** {len(name_changes)}\n"
              f"• **✅ لم يتغير:** {len(no_changes)}\n"
              f"• **❌ فشل التحقق:** {len(failed_updates)}",
        inline=False
    )
    
    await ctx.send(embed=embed)
    
    # 🔥 عرض التغييرات مع التقسيم إلى صفحات
    if name_changes:
        if len(name_changes) <= 50:  # إذا عدد التغييرات قليل
            changes_text = "\n".join(name_changes)
            changes_embed = discord.Embed(
                title=f"🔄 التغييرات ({len(name_changes)})",
                description=changes_text,
                color=discord.Color.orange()
            )
            await ctx.send(embed=changes_embed)
        else:
            # استخدام التقسيم إلى صفحات
            changes_pages = create_paginated_embeds(
                name_changes, 
                f"🔄 التغييرات ({len(name_changes)})",
                items_per_page=30,
                color=discord.Color.orange()
            )
            
            if len(changes_pages) == 1:
                await ctx.send(embed=changes_pages[0])
            else:
                view = PaginationView(changes_pages)
                await ctx.send(embed=changes_pages[0], view=view)
    
    # عرض الفاشلين
    if failed_updates:
        failed_text = "\n".join([f"• {name}" for name in failed_updates[:50]])
        
        if len(failed_updates) > 50:
            failed_text += f"\n... و{len(failed_updates) - 50} آخرين"
        
        failed_embed = discord.Embed(
            title=f"⚠️ فشل التحقق ({len(failed_updates)})",
            description=failed_text,
            color=discord.Color.red()
        )
        await ctx.send(embed=failed_embed)

@bot.command()
async def playerinfo(ctx, *, identifier):
    """معلومات عن لاعب مع التحقق من تغيير الأسماء"""
    
    data = load_data()
    history_data = load_name_history()
    
    # البحث عن اللاعب في القائمة أولاً
    target_uuid = None
    current_name = None
    in_list = False
    
    # البحث بالاسم في القائمة
    for uuid, name in data.items():
        if identifier.lower() == name.lower():
            target_uuid = uuid
            current_name = name
            in_list = True
            break
    
    # إذا لم يتم العثور في القائمة، جرب البحث في API
    if not target_uuid:
        # التحقق إذا كان UUID
        if is_valid_uuid(identifier):
            target_uuid = identifier
            current_name = await get_username_from_uuid(target_uuid)
        else:
            # البحث بالاسم في API
            target_uuid, current_name = await get_uuid_from_username(identifier)
    
    if not target_uuid or not current_name:
        await ctx.send(f"❌ لم يتم العثور على اللاعب: **{identifier}**")
        return
    
    # 🔥 الجزء الجديد: التحقق من تغيير الاسم إذا كان في القائمة
    name_changed = False
    original_name = None
    name_change_info = ""
    
    if in_list:
        stored_name = data.get(target_uuid)
        if stored_name and stored_name != current_name:
            name_changed = True
            original_name = stored_name
            name_change_info = f"🔄 **غير اسمه من:** `{stored_name}`\n✅ **الاسم الحالي:** `{current_name}`"
            
            # تحديث الاسم في القائمة
            data[target_uuid] = current_name
            save_data(data)
            
            # إضافة لتاريخ الأسماء
            add_name_history(target_uuid, stored_name, current_name)
            add_log_entry("NAME_CHANGE", "SYSTEM", f"{stored_name} → {current_name}", f"UUID: {target_uuid}")
    
    # إنشاء الـ Embed
    embed = discord.Embed(
        title=f"🔍 معلومات اللاعب: {current_name}",
        color=discord.Color.blue()
    )
    
    embed.add_field(name="🆔 UUID", value=f"`{target_uuid}`", inline=False)
    embed.add_field(name="📛 الاسم الحالي", value=current_name, inline=True)
    
    # حالة القائمة
    if in_list:
        status = "✅ مضاف للقائمة"
        if name_changed:
            status += " (تم تحديث الاسم)"
    else:
        status = "❌ غير مضاف"
    embed.add_field(name="📋 حالة القائمة", value=status, inline=True)
    
    # 🔥 عرض معلومات تغيير الاسم إذا حصل
    if name_changed:
        embed.add_field(name="🔄 تغيير الاسم", value=name_change_info, inline=False)
        embed.color = discord.Color.orange()  # تغيير اللون للإشارة للتغيير
    
    # 🔥 عرض تاريخ الأسماء المحفوظ لدينا
    if target_uuid in history_data and history_data[target_uuid]:
        name_history = history_data[target_uuid][-5:]  # آخر 5 تغييرات
        history_text = ""
        for change in reversed(name_history):
            history_text += f"`{change['old_name']}` → `{change['new_name']}`\n"
        
        embed.add_field(
            name=f"🕒 تاريخ الأسماء ({len(name_history)} تغيير)",
            value=history_text,
            inline=False
        )
    
    # معلومات إضافية
    embed.add_field(
        name="💾 مصدر البيانات", 
        value="Mojang API + قاعدة البيانات المحلية", 
        inline=False
    )
    
    await ctx.send(embed=embed)

@bot.command()
async def namehistory(ctx, *, identifier):
    """عرض تاريخ الأسماء الكامل للاعب"""
    
    data = load_data()
    history_data = load_name_history()
    
    # البحث عن اللاعب
    target_uuid = None
    current_name = None
    
    # البحث بالاسم أولاً في القائمة
    for uuid, name in data.items():
        if identifier.lower() == name.lower():
            target_uuid = uuid
            current_name = name
            break
    
    # إذا لم يتم العثور، جرب البحث في API
    if not target_uuid:
        if is_valid_uuid(identifier):
            target_uuid = identifier
            current_name = await get_username_from_uuid(target_uuid)
        else:
            target_uuid, current_name = await get_uuid_from_username(identifier)
    
    if not target_uuid or not current_name:
        await ctx.send(f"❌ لم يتم العثور على اللاعب: **{identifier}**")
        return
    
    if target_uuid not in history_data or not history_data[target_uuid]:
        await ctx.send(f"ℹ️ لا يوجد تاريخ أسماء مسجل لـ **{current_name}**")
        return
    
    name_history = history_data[target_uuid]
    name_history.reverse()  # عرض من الأحدث للأقدم
    
    history_entries = []
    for change in name_history:
        history_entries.append(
            f"`{change['timestamp']}`\n"
            f"`{change['old_name']}` → `{change['new_name']}`\n"
        )
    
    embed = discord.Embed(
        title=f"🕒 تاريخ الأسماء: {current_name}",
        description="\n".join(history_entries),
        color=discord.Color.teal()
    )
    
    await ctx.send(embed=embed)

@bot.command()
async def findplayer(ctx, *, search_term):
    """البحث عن لاعب في القائمة"""
    data = load_data()
    found_players = []
    
    for uuid, name in data.items():
        if search_term.lower() in name.lower():
            found_players.append(name)
    
    if found_players:
        players_text = "\n".join([f"• {name}" for name in found_players])
        embed = discord.Embed(
            title=f"🔍 نتائج البحث عن: {search_term}",
            description=players_text,
            color=discord.Color.green()
        )
    else:
        embed = discord.Embed(
            title="🔍 نتائج البحث",
            description=f"❌ لم يتم العثور على: **{search_term}**",
            color=discord.Color.orange()
        )
    
    await ctx.send(embed=embed)

@bot.command()
async def listinfo(ctx):
    """إحصائيات القائمة"""
    data = load_data()
    player_count = len(data)
    
    embed = discord.Embed(
        title="📊 إحصائيات القائمة",
        color=discord.Color.gold()
    )
    
    embed.add_field(name="👥 عدد اللاعبين", value=player_count, inline=True)
    
    if player_count > 0:
        sample_players = list(data.values())[:5]
        embed.add_field(
            name="أمثلة من اللاعبين", 
            value=", ".join(sample_players) + ("..." if player_count > 5 else ""), 
            inline=False
        )
    
    await ctx.send(embed=embed)

@bot.command()
async def showlist(ctx, page: int = 1):
    """عرض قائمة اللاعبين بصفحة محددة"""
    data = load_data()
    
    if not data:
        await ctx.send("📭 القائمة فارغة")
        return
    
    players_list = [f"• {name}" for name in data.values()]
    items_per_page = 25
    
    # حساب عدد الصفحات
    total_pages = (len(players_list) + items_per_page - 1) // items_per_page
    
    if page < 1 or page > total_pages:
        await ctx.send(f"❌ رقم الصفحة يجب أن يكون بين 1 و {total_pages}")
        return
    
    # حساب بداية ونهاية الصفحة
    start_idx = (page - 1) * items_per_page
    end_idx = start_idx + items_per_page
    
    page_items = players_list[start_idx:end_idx]
    page_text = "\n".join(page_items)
    
    embed = discord.Embed(
        title=f"📋 قائمة اللاعبين - الصفحة {page}/{total_pages}",
        description=page_text,
        color=discord.Color.blue()
    )
    embed.set_footer(text=f"إجمالي اللاعبين: {len(players_list)}")
    
    await ctx.send(embed=embed)


@bot.command()
async def log(ctx, count: int = 50):
    """عرض سجل التغييرات مع تقسيم إلى صفحات"""
    log_data = load_log()
    
    if not log_data:
        await ctx.send("📋 لا توجد سجلات حتى الآن")
        return
    
    # تقييد العدد المسموح
    count = min(count, 200)
    
    recent_logs = log_data[-count:]
    recent_logs.reverse()
    
    # إنشاء السجلات بشكل منظم أكثر
    log_entries = []
    for entry in recent_logs:
        action_emoji = {
            "ADD": "📥",
            "ADD_UUID": "📥", 
            "REMOVE": "🗑️",
            "NAME_CHANGE": "🔄",
            "NAME_UPDATE": "🔄",
            "ADD_CUSTOM": "🎮",
            "REMOVE_CUSTOM": "🗑️🎮"
        }.get(entry["action"], "📝")
        
        # تنسيق أقصر وأفضل
        timestamp_short = entry['timestamp'].split()[1]  # الوقت فقط (الساعة)
        log_entry = f"{action_emoji} **{entry['action']}**\n"
        log_entry += f"⏰ {timestamp_short} | 👤 {entry['user'][:15]}\n"
        log_entry += f"🎯 {entry['target'][:25]}"
        
        if entry["details"]:
            # إظهار جزء من التفاصيل
            details_short = entry["details"][:30] + "..." if len(entry["details"]) > 30 else entry["details"]
            log_entry += f"\n📄 {details_short}"
        
        log_entries.append(log_entry)
    
    # 🔥 تقسيم السجلات إلى صفحات (8 سجلات في الصفحة)
    items_per_page = 8
    
    if len(log_entries) <= items_per_page:
        log_text = "\n\n".join(log_entries)
        
        embed = discord.Embed(
            title=f"📋 سجل التغييرات - {len(recent_logs)} عملية",
            description=log_text,
            color=discord.Color.purple()
        )
        
        if recent_logs:
            date_range = f"من {recent_logs[-1]['timestamp'].split()[0]} إلى {recent_logs[0]['timestamp'].split()[0]}"
            embed.set_footer(text=date_range)
        
        await ctx.send(embed=embed)
        return
    
    # إنشاء الصفحات
    pages = []
    total_pages = (len(log_entries) + items_per_page - 1) // items_per_page
    
    for i in range(0, len(log_entries), items_per_page):
        page_entries = log_entries[i:i + items_per_page]
        page_text = "\n\n".join(page_entries)
        
        page_num = i // items_per_page + 1
        
        embed = discord.Embed(
            title=f"📋 سجل التغييرات - الصفحة {page_num}/{total_pages}",
            description=page_text,
            color=discord.Color.purple()
        )
        
        # إضافة معلومات عن الصفحة في التذييل
        start_entry = i + 1
        end_entry = min(i + items_per_page, len(log_entries))
        embed.set_footer(text=f"السجلات {start_entry}-{end_entry} من {len(recent_logs)} | المجموع: {len(recent_logs)} سجل")
        
        pages.append(embed)
    
    # إرسال مع أزرار التنقل
    view = PaginationView(pages, show_extreme_buttons=True)
    await ctx.send(embed=pages[0], view=view)

@bot.command()
async def logsearch(ctx, *, search_term):
    """البحث في سجل التغييرات"""
    log_data = load_log()
    
    if not log_data:
        await ctx.send("📋 لا توجد سجلات حتى الآن")
        return
    
    # البحث في السجلات
    results = []
    for entry in reversed(log_data):  # البحث من الأحدث
        if (search_term.lower() in entry["user"].lower() or 
            search_term.lower() in entry["target"].lower() or
            search_term.lower() in entry["action"].lower() or
            search_term.lower() in entry.get("details", "").lower()):
            results.append(entry)
            
            if len(results) >= 100:  # الحد الأقصى للنتائج
                break
    
    if not results:
        await ctx.send(f"🔍 لم يتم العثور على نتائج للبحث: **{search_term}**")
        return
    
    # تحويل النتائج إلى تنسيق قابل للعرض
    result_entries = []
    for entry in results:
        action_emoji = {
            "ADD": "📥",
            "ADD_UUID": "📥", 
            "REMOVE": "🗑️",
            "NAME_CHANGE": "🔄",
            "NAME_UPDATE": "🔄",
            "ADD_CUSTOM": "🎮",
            "REMOVE_CUSTOM": "🗑️🎮"
        }.get(entry["action"], "📝")
        
        timestamp_short = entry['timestamp'].split()[1]
        result_entry = f"{action_emoji} **{entry['action']}** | {timestamp_short}\n"
        result_entry += f"👤 {entry['user'][:15]} | 🎯 {entry['target'][:20]}"
        
        if entry["details"]:
            details_short = entry["details"][:25] + "..." if len(entry["details"]) > 25 else entry["details"]
            result_entry += f"\n📄 {details_short}"
        
        result_entries.append(result_entry)
    
    # تقسيم النتائج إلى صفحات
    items_per_page = 8
    pages = []
    total_pages = (len(result_entries) + items_per_page - 1) // items_per_page
    
    for i in range(0, len(result_entries), items_per_page):
        page_entries = result_entries[i:i + items_per_page]
        page_text = "\n\n".join(page_entries)
        
        page_num = i // items_per_page + 1
        
        embed = discord.Embed(
            title=f"🔍 نتائج البحث: {search_term}",
            description=page_text,
            color=discord.Color.green()
        )
        
        embed.set_footer(text=f"الصفحة {page_num}/{total_pages} | {len(results)} نتيجة")
        
        pages.append(embed)
    
    if len(pages) == 1:
        await ctx.send(embed=pages[0])
    else:
        view = PaginationView(pages, show_extreme_buttons=True)
        await ctx.send(embed=pages[0], view=view)

@bot.command()
async def clearlog(ctx):
    """مسح سجل التغييرات"""
    log_data = load_log()
    
    if not log_data:
        await ctx.send("📋 السجل فارغ بالفعل")
        return
    
    # تأكيد المسح
    confirm_msg = await ctx.send(
        f"⚠️ هل تريد مسح **{len(log_data)}** سجل؟\n"
        f"تفاعل بـ ✅ للتأكيد أو ❌ للإلغاء"
    )
    await confirm_msg.add_reaction("✅")
    await confirm_msg.add_reaction("❌")
    
    def check(reaction, user):
        return user == ctx.author and str(reaction.emoji) in ["✅", "❌"]
    
    try:
        reaction, user = await bot.wait_for('reaction_add', timeout=30.0, check=check)
        if str(reaction.emoji) == "✅":
            # حفظ سجل فارغ
            save_log([])
            await confirm_msg.edit(content="✅ تم مسح سجل التغييرات بالكامل")
        else:
            await confirm_msg.edit(content="❌ تم الإلغاء")
    except asyncio.TimeoutError:
        await confirm_msg.edit(content="❌ انتهى وقت الانتظار")

# تشغيل البوت
bot.run("YOUR TOKEN HERE!")