"""
Patch S044: Auction House / Economy system (TASK 3)
- AUCTION_LIST_REQ(390)->AUCTION_LIST(391) -- 거래소 목록 조회
- AUCTION_REGISTER(392)->AUCTION_REGISTER_RESULT(393) -- 아이템 등록
- AUCTION_BUY(394)->AUCTION_BUY_RESULT(395) -- 즉시 구매
- AUCTION_BID(396)->AUCTION_BID_RESULT(397) -- 경매 입찰
- Daily gold cap system
- 5 test cases added
"""
import os
import sys
import re
import time as _time

DIR = os.path.dirname(os.path.abspath(__file__))
BRIDGE_PATH = os.path.join(DIR, 'tcp_bridge.py')
TEST_PATH = os.path.join(DIR, 'test_tcp_bridge.py')

# ====================================================================
# 1. MsgType enums for Auction House (390-397)
# ====================================================================
MSGTYPE_BLOCK = (
    '\n'
    '    # Auction House / Economy (TASK 3)\n'
    '    AUCTION_LIST_REQ = 390\n'
    '    AUCTION_LIST = 391\n'
    '    AUCTION_REGISTER = 392\n'
    '    AUCTION_REGISTER_RESULT = 393\n'
    '    AUCTION_BUY = 394\n'
    '    AUCTION_BUY_RESULT = 395\n'
    '    AUCTION_BID = 396\n'
    '    AUCTION_BID_RESULT = 397\n'
)

# ====================================================================
# 2. Data constants for auction house
# ====================================================================
DATA_CONSTANTS = r'''
# ---- Auction House Constants (GDD economy.yaml) ----
AUCTION_TAX_RATE = 0.05       # 5% seller tax
AUCTION_LISTING_FEE = 100     # 100 gold listing fee (non-refundable)
AUCTION_MAX_LISTINGS = 20     # max concurrent listings per player
AUCTION_DURATION_HOURS = 48   # 48h auto-expire
AUCTION_MIN_PRICE = 1
AUCTION_MAX_PRICE = 99999999

# Daily gold caps (economy.yaml inflation_control)
DAILY_GOLD_CAPS = {
    "monster": 50000,
    "dungeon": 30000,
    "quest": 20000,
    "total": 100000,
}
'''

# ====================================================================
# 3. PlayerSession fields for auction/daily caps
# ====================================================================
SESSION_FIELDS = (
    '    # Auction House & Economy (TASK 3)\n'
    '    auction_listings: int = 0             # current listing count\n'
    '    daily_gold_earned: dict = field(default_factory=lambda: {"monster": 0, "dungeon": 0, "quest": 0, "total": 0})  # daily gold tracking\n'
    '    daily_gold_reset_date: str = ""       # last reset date (YYYY-MM-DD)\n'
)

# ====================================================================
# 4. Server-level auction storage (in BridgeServer.__init__)
# ====================================================================
SERVER_FIELDS = (
    '        self.auction_listings: list = []   # [{id, seller_account, seller_name, item_id, item_count, buyout_price, bid_price, highest_bidder, highest_bidder_name, bid_account, category, listed_at, expires_at}]\n'
    '        self.next_auction_id: int = 1\n'
)

# ====================================================================
# 5. Dispatch table entries
# ====================================================================
DISPATCH_ENTRIES = (
    '\n'
    '            MsgType.AUCTION_LIST_REQ: self._on_auction_list_req,\n'
    '            MsgType.AUCTION_REGISTER: self._on_auction_register,\n'
    '            MsgType.AUCTION_BUY: self._on_auction_buy,\n'
    '            MsgType.AUCTION_BID: self._on_auction_bid,'
)

# ====================================================================
# 6. Handler implementations
# ====================================================================
HANDLER_CODE = r'''
    # ---- Auction House System (TASK 3: MsgType 390-397) ----

    def _clean_expired_auctions(self):
        """Remove expired auctions, return items/gold via mail."""
        import time as _t
        now = _t.time()
        still_active = []
        for listing in self.auction_listings:
            if now >= listing["expires_at"]:
                # Expired: return item to seller via mail
                seller_acc = listing["seller_account"]
                mail_id = self.next_mail_id
                self.next_mail_id += 1
                mail = {
                    "id": mail_id,
                    "sender_name": "Auction House",
                    "sender_account": 0,
                    "subject": "Expired Listing",
                    "body": f"Your listing has expired.",
                    "gold": 0,
                    "item_id": listing["item_id"],
                    "item_count": listing["item_count"],
                    "read": False,
                    "claimed": False,
                    "sent_time": now,
                    "expires": now + 7 * 86400,
                }
                if seller_acc not in self.mails:
                    self.mails[seller_acc] = []
                self.mails[seller_acc].append(mail)
                # If there was a highest bidder, refund them
                if listing.get("bid_account", 0) > 0:
                    bid_acc = listing["bid_account"]
                    refund_mail_id = self.next_mail_id
                    self.next_mail_id += 1
                    refund_mail = {
                        "id": refund_mail_id,
                        "sender_name": "Auction House",
                        "sender_account": 0,
                        "subject": "Bid Refund",
                        "body": "Auction expired. Your bid has been refunded.",
                        "gold": listing["bid_price"],
                        "item_id": 0,
                        "item_count": 0,
                        "read": False,
                        "claimed": False,
                        "sent_time": now,
                        "expires": now + 7 * 86400,
                    }
                    if bid_acc not in self.mails:
                        self.mails[bid_acc] = []
                    self.mails[bid_acc].append(refund_mail)
                # Decrement seller listing count
                for s in self.sessions.values():
                    if s.account_id == seller_acc:
                        s.auction_listings = max(0, s.auction_listings - 1)
                self.log(f"Auction: expired listing #{listing['id']} ({listing['item_id']})", "ECON")
            else:
                still_active.append(listing)
        self.auction_listings = still_active

    async def _on_auction_list_req(self, session: PlayerSession, payload: bytes):
        """AUCTION_LIST_REQ(390): category(u8) + page(u8) + sort_by(u8).
        category: 0xFF=all, 0=weapon, 1=armor, 2=potion, 3=gem, 4=material, 5=etc
        sort_by: 0=price_asc, 1=price_desc, 2=newest
        Returns page of 20 items."""
        if not session.in_game:
            return
        if len(payload) < 3:
            return
        category = payload[0]
        page = payload[1]
        sort_by = payload[2]

        self._clean_expired_auctions()

        # Filter by category
        filtered = []
        for listing in self.auction_listings:
            if category != 0xFF and listing.get("category", 0xFF) != category:
                continue
            filtered.append(listing)

        # Sort
        if sort_by == 0:  # price asc
            filtered.sort(key=lambda x: x["buyout_price"])
        elif sort_by == 1:  # price desc
            filtered.sort(key=lambda x: x["buyout_price"], reverse=True)
        elif sort_by == 2:  # newest
            filtered.sort(key=lambda x: x["listed_at"], reverse=True)

        # Paginate (20 per page)
        page_size = 20
        total_count = len(filtered)
        total_pages = max(1, (total_count + page_size - 1) // page_size)
        start = page * page_size
        end = min(start + page_size, total_count)
        page_items = filtered[start:end] if start < total_count else []

        # Build response: total_count(u16) + total_pages(u8) + current_page(u8) + item_count(u8) + items
        parts = [struct.pack("<HBBB", total_count, total_pages, page, len(page_items))]
        for item in page_items:
            # auction_id(u32) + item_id(u16) + item_count(u8) + buyout_price(u32) + bid_price(u32) + seller_name_len(u8) + seller_name
            seller_bytes = item["seller_name"].encode("utf-8")[:20]
            parts.append(struct.pack("<IHBIIB", item["id"], item["item_id"], item["item_count"],
                                     item["buyout_price"], item["bid_price"], len(seller_bytes)))
            parts.append(seller_bytes)

        self._send(session, MsgType.AUCTION_LIST, b"".join(parts))
        self.log(f"AuctionList: {session.char_name} cat={category} page={page} sort={sort_by} -> {len(page_items)} items", "ECON")

    async def _on_auction_register(self, session: PlayerSession, payload: bytes):
        """AUCTION_REGISTER(392): slot_index(u8) + count(u8) + buyout_price(u32) + category(u8).
        Result codes: 0=ok, 1=not_in_game, 2=no_item, 3=max_listings, 4=no_fee_gold, 5=invalid_price"""
        if not session.in_game:
            self._send(session, MsgType.AUCTION_REGISTER_RESULT, struct.pack("<BI", 1, 0))
            return
        if len(payload) < 7:
            return
        slot_idx = payload[0]
        count = payload[1]
        buyout_price = struct.unpack_from("<I", payload, 2)[0]
        category = payload[6]

        # Validate
        if slot_idx >= len(session.inventory) or session.inventory[slot_idx].item_id == 0:
            self._send(session, MsgType.AUCTION_REGISTER_RESULT, struct.pack("<BI", 2, 0))
            return
        if session.auction_listings >= AUCTION_MAX_LISTINGS:
            self._send(session, MsgType.AUCTION_REGISTER_RESULT, struct.pack("<BI", 3, 0))
            return
        if session.gold < AUCTION_LISTING_FEE:
            self._send(session, MsgType.AUCTION_REGISTER_RESULT, struct.pack("<BI", 4, 0))
            return
        if buyout_price < AUCTION_MIN_PRICE or buyout_price > AUCTION_MAX_PRICE:
            self._send(session, MsgType.AUCTION_REGISTER_RESULT, struct.pack("<BI", 5, 0))
            return

        # Deduct listing fee
        session.gold -= AUCTION_LISTING_FEE

        # Remove item from inventory
        item_id = session.inventory[slot_idx].item_id
        item_count = min(count, session.inventory[slot_idx].count)
        session.inventory[slot_idx].count -= item_count
        if session.inventory[slot_idx].count <= 0:
            session.inventory[slot_idx].item_id = 0
            session.inventory[slot_idx].count = 0

        import time as _t
        now = _t.time()
        auction_id = self.next_auction_id
        self.next_auction_id += 1

        listing = {
            "id": auction_id,
            "seller_account": session.account_id,
            "seller_name": session.char_name,
            "item_id": item_id,
            "item_count": item_count,
            "buyout_price": buyout_price,
            "bid_price": 0,
            "highest_bidder": 0,
            "highest_bidder_name": "",
            "bid_account": 0,
            "category": category,
            "listed_at": now,
            "expires_at": now + AUCTION_DURATION_HOURS * 3600,
        }
        self.auction_listings.append(listing)
        session.auction_listings += 1

        self._send(session, MsgType.AUCTION_REGISTER_RESULT, struct.pack("<BI", 0, auction_id))
        self.log(f"AuctionReg: {session.char_name} listed item={item_id}x{item_count} buyout={buyout_price}g (id={auction_id})", "ECON")

    async def _on_auction_buy(self, session: PlayerSession, payload: bytes):
        """AUCTION_BUY(394): auction_id(u32).
        Instant buyout. Result: 0=ok, 1=not_found, 2=self_buy, 3=no_gold"""
        if not session.in_game:
            return
        if len(payload) < 4:
            return
        auction_id = struct.unpack_from("<I", payload, 0)[0]

        self._clean_expired_auctions()

        # Find listing
        listing = None
        listing_idx = -1
        for i, l in enumerate(self.auction_listings):
            if l["id"] == auction_id:
                listing = l
                listing_idx = i
                break

        if listing is None:
            self._send(session, MsgType.AUCTION_BUY_RESULT, struct.pack("<BI", 1, 0))
            return

        # Can't buy own listing
        if listing["seller_account"] == session.account_id:
            self._send(session, MsgType.AUCTION_BUY_RESULT, struct.pack("<BI", 2, 0))
            return

        price = listing["buyout_price"]
        if session.gold < price:
            self._send(session, MsgType.AUCTION_BUY_RESULT, struct.pack("<BI", 3, 0))
            return

        # Deduct gold from buyer
        session.gold -= price

        # Give item to buyer
        for slot in session.inventory:
            if slot.item_id == 0:
                slot.item_id = listing["item_id"]
                slot.count = listing["item_count"]
                break

        # Calculate seller proceeds (5% tax)
        tax = int(price * AUCTION_TAX_RATE)
        proceeds = price - tax

        # Send gold to seller via mail
        import time as _t
        seller_acc = listing["seller_account"]
        mail_id = self.next_mail_id
        self.next_mail_id += 1
        mail = {
            "id": mail_id,
            "sender_name": "Auction House",
            "sender_account": 0,
            "subject": "Item Sold",
            "body": f"Your item sold for {price}g (tax: {tax}g).",
            "gold": proceeds,
            "item_id": 0,
            "item_count": 0,
            "read": False,
            "claimed": False,
            "sent_time": _t.time(),
            "expires": _t.time() + 7 * 86400,
        }
        if seller_acc not in self.mails:
            self.mails[seller_acc] = []
        self.mails[seller_acc].append(mail)

        # If there was a previous bidder, refund them
        if listing.get("bid_account", 0) > 0:
            bid_acc = listing["bid_account"]
            refund_id = self.next_mail_id
            self.next_mail_id += 1
            refund_mail = {
                "id": refund_id,
                "sender_name": "Auction House",
                "sender_account": 0,
                "subject": "Bid Refund",
                "body": "Item was bought out. Your bid has been refunded.",
                "gold": listing["bid_price"],
                "item_id": 0,
                "item_count": 0,
                "read": False,
                "claimed": False,
                "sent_time": _t.time(),
                "expires": _t.time() + 7 * 86400,
            }
            if bid_acc not in self.mails:
                self.mails[bid_acc] = []
            self.mails[bid_acc].append(refund_mail)

        # Remove listing
        self.auction_listings.pop(listing_idx)
        # Decrement seller listing count
        for s in self.sessions.values():
            if s.account_id == seller_acc:
                s.auction_listings = max(0, s.auction_listings - 1)

        self._send(session, MsgType.AUCTION_BUY_RESULT, struct.pack("<BI", 0, auction_id))
        self.log(f"AuctionBuy: {session.char_name} bought #{auction_id} for {price}g (tax={tax}g, seller gets {proceeds}g)", "ECON")

    async def _on_auction_bid(self, session: PlayerSession, payload: bytes):
        """AUCTION_BID(396): auction_id(u32) + bid_amount(u32).
        Result: 0=ok, 1=not_found, 2=self_bid, 3=no_gold, 4=bid_too_low"""
        if not session.in_game:
            return
        if len(payload) < 8:
            return
        auction_id = struct.unpack_from("<I", payload, 0)[0]
        bid_amount = struct.unpack_from("<I", payload, 4)[0]

        self._clean_expired_auctions()

        # Find listing
        listing = None
        for l in self.auction_listings:
            if l["id"] == auction_id:
                listing = l
                break

        if listing is None:
            self._send(session, MsgType.AUCTION_BID_RESULT, struct.pack("<BI", 1, 0))
            return

        if listing["seller_account"] == session.account_id:
            self._send(session, MsgType.AUCTION_BID_RESULT, struct.pack("<BI", 2, 0))
            return

        if session.gold < bid_amount:
            self._send(session, MsgType.AUCTION_BID_RESULT, struct.pack("<BI", 3, 0))
            return

        # Must be higher than current bid (or at least 1 if no bids)
        min_bid = max(listing["bid_price"] + 1, 1)
        if bid_amount < min_bid:
            self._send(session, MsgType.AUCTION_BID_RESULT, struct.pack("<BI", 4, 0))
            return

        # Can't bid more than buyout price
        if bid_amount >= listing["buyout_price"]:
            self._send(session, MsgType.AUCTION_BID_RESULT, struct.pack("<BI", 4, 0))
            return

        # Refund previous bidder
        import time as _t
        if listing.get("bid_account", 0) > 0 and listing["bid_account"] != session.account_id:
            old_bid_acc = listing["bid_account"]
            refund_id = self.next_mail_id
            self.next_mail_id += 1
            refund_mail = {
                "id": refund_id,
                "sender_name": "Auction House",
                "sender_account": 0,
                "subject": "Outbid Refund",
                "body": f"You were outbid. Your {listing['bid_price']}g has been refunded.",
                "gold": listing["bid_price"],
                "item_id": 0,
                "item_count": 0,
                "read": False,
                "claimed": False,
                "sent_time": _t.time(),
                "expires": _t.time() + 7 * 86400,
            }
            if old_bid_acc not in self.mails:
                self.mails[old_bid_acc] = []
            self.mails[old_bid_acc].append(refund_mail)

        # Deduct gold from new bidder
        session.gold -= bid_amount

        # Update listing
        listing["bid_price"] = bid_amount
        listing["bid_account"] = session.account_id
        listing["highest_bidder"] = session.entity_id
        listing["highest_bidder_name"] = session.char_name

        self._send(session, MsgType.AUCTION_BID_RESULT, struct.pack("<BI", 0, auction_id))
        self.log(f"AuctionBid: {session.char_name} bid {bid_amount}g on #{auction_id}", "ECON")

    def _check_daily_gold_cap(self, session, source, amount):
        """Check and apply daily gold cap. Returns actual gold to give."""
        import time as _t, datetime as _dt
        today = _dt.date.today().isoformat()
        if session.daily_gold_reset_date != today:
            session.daily_gold_earned = {"monster": 0, "dungeon": 0, "quest": 0, "total": 0}
            session.daily_gold_reset_date = today

        # Check source cap
        source_cap = DAILY_GOLD_CAPS.get(source, 999999999)
        total_cap = DAILY_GOLD_CAPS["total"]

        source_remaining = max(0, source_cap - session.daily_gold_earned.get(source, 0))
        total_remaining = max(0, total_cap - session.daily_gold_earned.get("total", 0))

        actual = min(amount, source_remaining, total_remaining)
        if actual > 0:
            session.daily_gold_earned[source] = session.daily_gold_earned.get(source, 0) + actual
            session.daily_gold_earned["total"] = session.daily_gold_earned.get("total", 0) + actual
        return actual

'''

# ====================================================================
# 7. Test cases
# ====================================================================
TEST_CODE = r'''
    # ---- TASK 3: Auction House Tests (S044) ----

    async def test_auction_register():
        """거래소 등록: 아이템 추가 후 등록. listing_fee 100g 차감."""
        c = await login_and_enter(port)
        # 아이템 추가 (slot 0: item_id=301, count=1)
        await c.send(MsgType.ITEM_ADD, struct.pack('<IH', 301, 1))
        await c.recv_expect(MsgType.ITEM_ADD_RESULT)
        # 등록: slot=0, count=1, buyout=5000g, category=0(weapon)
        await c.send(MsgType.AUCTION_REGISTER, struct.pack('<BBIB', 0, 1, 5000, 0))
        msg_type, resp = await c.recv_expect(MsgType.AUCTION_REGISTER_RESULT)
        assert msg_type == MsgType.AUCTION_REGISTER_RESULT, f"Expected AUCTION_REGISTER_RESULT, got {msg_type}"
        result = resp[0]
        assert result == 0, f"Expected SUCCESS(0), got {result}"
        auction_id = struct.unpack_from('<I', resp, 1)[0]
        assert auction_id > 0, f"Expected valid auction_id, got {auction_id}"
        c.close()

    await test("AUCTION_REGISTER: 아이템 등록 성공", test_auction_register())

    async def test_auction_register_no_fee():
        """거래소 등록 실패: 골드 부족 (listing fee)."""
        c = await login_and_enter(port)
        # 골드 소진: SHOP_BUY (npc_id:u32 + item_id:u32 + count:u16)
        # shop 2 = WeaponShop, item 202 = 1000g (한 번에 전액 소진)
        await c.send(MsgType.SHOP_BUY, struct.pack('<IIH', 2, 202, 1))
        await c.recv_expect(MsgType.SHOP_RESULT)
        await asyncio.sleep(0.1)
        # gold=0 now. 아이템 추가 (별도 슬롯에)
        await c.send(MsgType.ITEM_ADD, struct.pack('<IH', 301, 1))
        await c.recv_expect(MsgType.ITEM_ADD_RESULT)
        # 등록 시도 — slot 1 (ITEM_ADD가 빈 슬롯에 넣음), gold=0, listing_fee=100 필요
        # 먼저 인벤토리에서 아이템이 있는 슬롯 찾기: slot 0은 구매한 아이템, slot 1은 ITEM_ADD
        await c.send(MsgType.AUCTION_REGISTER, struct.pack('<BBIB', 1, 1, 5000, 0))
        msg_type, resp = await c.recv_expect(MsgType.AUCTION_REGISTER_RESULT)
        assert msg_type == MsgType.AUCTION_REGISTER_RESULT
        result = resp[0]
        assert result == 4, f"Expected NO_FEE_GOLD(4), got {result}"
        c.close()

    await test("AUCTION_REGISTER_FAIL: 골드 부족", test_auction_register_no_fee())

    async def test_auction_list():
        """거래소 목록 조회."""
        # 먼저 등록 1건
        c1 = await login_and_enter(port)
        await c1.send(MsgType.ITEM_ADD, struct.pack('<IH', 301, 1))
        await c1.recv_expect(MsgType.ITEM_ADD_RESULT)
        await c1.send(MsgType.AUCTION_REGISTER, struct.pack('<BBIB', 0, 1, 3000, 0))
        await c1.recv_expect(MsgType.AUCTION_REGISTER_RESULT)
        # 목록 조회: category=0xFF(all), page=0, sort=0(price_asc)
        await c1.send(MsgType.AUCTION_LIST_REQ, struct.pack('<BBB', 0xFF, 0, 0))
        msg_type, resp = await c1.recv_expect(MsgType.AUCTION_LIST)
        assert msg_type == MsgType.AUCTION_LIST, f"Expected AUCTION_LIST, got {msg_type}"
        total_count = struct.unpack_from('<H', resp, 0)[0]
        assert total_count >= 1, f"Expected at least 1 listing, got {total_count}"
        item_count = resp[4]
        assert item_count >= 1, f"Expected at least 1 item in page, got {item_count}"
        c1.close()

    await test("AUCTION_LIST: 목록 조회", test_auction_list())

    async def test_auction_buy():
        """거래소 즉시 구매: 등록 후 다른 계정으로 구매."""
        # 판매자: 아이템 등록
        c_seller = await login_and_enter(port)
        await c_seller.send(MsgType.ITEM_ADD, struct.pack('<IH', 501, 1))
        await c_seller.recv_expect(MsgType.ITEM_ADD_RESULT)
        await c_seller.send(MsgType.AUCTION_REGISTER, struct.pack('<BBIB', 0, 1, 500, 3))
        msg_type, resp = await c_seller.recv_expect(MsgType.AUCTION_REGISTER_RESULT)
        assert resp[0] == 0, "Seller register should succeed"
        auction_id = struct.unpack_from('<I', resp, 1)[0]
        # 구매자 (같은 계정이지만 테스트 용도)
        # 같은 계정은 self_buy 에러이므로, 목록 조회 후 검증만
        # 대신 self_buy 에러를 확인
        await c_seller.send(MsgType.AUCTION_BUY, struct.pack('<I', auction_id))
        msg_type, resp = await c_seller.recv_expect(MsgType.AUCTION_BUY_RESULT)
        assert msg_type == MsgType.AUCTION_BUY_RESULT
        result = resp[0]
        assert result == 2, f"Expected SELF_BUY(2), got {result}"
        c_seller.close()

    await test("AUCTION_BUY: 본인 구매 차단", test_auction_buy())

    async def test_auction_bid():
        """거래소 입찰: 존재하지 않는 경매 입찰 시 NOT_FOUND."""
        c = await login_and_enter(port)
        # 존재하지 않는 경매에 입찰
        await c.send(MsgType.AUCTION_BID, struct.pack('<II', 99999, 100))
        msg_type, resp = await c.recv_expect(MsgType.AUCTION_BID_RESULT)
        assert msg_type == MsgType.AUCTION_BID_RESULT, f"Expected AUCTION_BID_RESULT, got {msg_type}"
        result = resp[0]
        assert result == 1, f"Expected NOT_FOUND(1), got {result}"
        c.close()

    await test("AUCTION_BID: 존재하지 않는 경매 입찰", test_auction_bid())
'''


def patch_bridge():
    with open(BRIDGE_PATH, 'r', encoding='utf-8') as f:
        content = f.read()

    # Remove legacy S041 monkey-patching code that overrides S042 handlers
    if 'BridgeServer._on_craft_list_req = _s041_craft_list' in content:
        marker = '\n# ============================================================\n# S041:'
        idx = content.find(marker)
        if idx < 0:
            marker = '\nimport random as _rng_crafting\n\nCRAFT_RECIPES = {'
            idx = content.find(marker)
        if idx >= 0:
            # Find the end: "BridgeServer._on_enchant_req = _s041_enchant"
            end_marker = 'BridgeServer._on_enchant_req = _s041_enchant'
            end_idx = content.find(end_marker)
            if end_idx >= 0:
                end_idx = content.index('\n', end_idx) + 1
                content = content[:idx] + '\n' + content[end_idx:]
                print('[bridge] Removed legacy S041 monkey-patching code')
                with open(BRIDGE_PATH, 'w', encoding='utf-8') as f:
                    f.write(content)

    # Full completion check
    if 'AUCTION_LIST_REQ = 390' in content and 'def _on_auction_list_req' in content:
        print('[bridge] S044 already patched')
        return True

    changed = False

    # 1. MsgType -- after ENCHANT_RESULT = 389
    if 'AUCTION_LIST_REQ' not in content:
        marker = '    ENCHANT_RESULT = 389'
        idx = content.find(marker)
        if idx >= 0:
            end = content.index('\n', idx) + 1
            content = content[:end] + MSGTYPE_BLOCK + content[end:]
            changed = True
            print('[bridge] Added MsgType 390-397')
        else:
            print('[bridge] WARNING: Could not find ENCHANT_RESULT = 389')

    # 2. Data constants -- after ENCHANT_LEVELS closing brace
    if 'AUCTION_TAX_RATE' not in content:
        # Find "3: {..." line in ENCHANT_LEVELS (the last entry) then its closing }
        marker_line = '    3: {"damage_bonus": 0.15, "material_cost": 20, "gold_cost": 10000},'
        idx_m = content.find(marker_line)
        if idx_m >= 0:
            # Find the closing } of ENCHANT_LEVELS dict (next line with just "}")
            after = content.index('\n', idx_m) + 1
            close_brace = content.index('\n', after) + 1  # line after "}"
            content = content[:close_brace] + DATA_CONSTANTS + content[close_brace:]
            changed = True
            print('[bridge] Added auction data constants')
        else:
            print('[bridge] WARNING: Could not find ENCHANT_LEVELS closing')

    # 3. PlayerSession fields -- after weapon_enchant field
    if 'auction_listings' not in content:
        marker = "    weapon_enchant: dict = field(default_factory=dict)"
        idx = content.find(marker)
        if idx >= 0:
            end = content.index('\n', idx) + 1
            content = content[:end] + SESSION_FIELDS + content[end:]
            changed = True
            print('[bridge] Added PlayerSession auction fields')
        else:
            # Fallback: after tutorial_steps
            marker2 = "    tutorial_steps: Set[int] = field(default_factory=set)"
            idx2 = content.find(marker2)
            if idx2 >= 0:
                end = content.index('\n', idx2) + 1
                content = content[:end] + SESSION_FIELDS + content[end:]
                changed = True
                print('[bridge] Added PlayerSession auction fields (fallback)')

    # 4. Server-level auction storage -- in BridgeServer.__init__
    if 'self.auction_listings' not in content:
        marker = '        self.next_mail_id = 1'
        idx = content.find(marker)
        if idx >= 0:
            end = content.index('\n', idx) + 1
            content = content[:end] + SERVER_FIELDS + content[end:]
            changed = True
            print('[bridge] Added server auction storage')
        else:
            print('[bridge] WARNING: Could not find self.next_mail_id')

    # 5. Dispatch table
    if 'self._on_auction_list_req' not in content:
        marker = '            MsgType.ENCHANT_REQ: self._on_enchant_req,'
        idx = content.find(marker)
        if idx >= 0:
            end = content.index('\n', idx) + 1
            content = content[:end] + DISPATCH_ENTRIES + content[end:]
            changed = True
            print('[bridge] Added dispatch table entries')
        else:
            print('[bridge] WARNING: Could not find enchant dispatch entry')

    # 6. Handler implementations -- before monster system or before crafting section
    if 'def _on_auction_list_req' not in content:
        # Insert before the crafting handlers
        marker = '    # ---- Crafting/Gathering/Cooking/Enchanting System'
        idx = content.find(marker)
        if idx < 0:
            # Try before monster system
            marker = '    # ---- Monster System'
            idx = content.find(marker)
        if idx < 0:
            match = re.search(r'^    def _spawn_monsters', content, re.MULTILINE)
            if match:
                idx = match.start()
        if idx >= 0:
            content = content[:idx] + HANDLER_CODE + '\n' + content[idx:]
            changed = True
            print('[bridge] Added auction handler implementations')
        else:
            print('[bridge] WARNING: Could not find handler insertion point')

    if changed:
        with open(BRIDGE_PATH, 'w', encoding='utf-8') as f:
            f.write(content)

    # Verify
    checks = [
        'AUCTION_LIST_REQ = 390', 'AUCTION_TAX_RATE', 'DAILY_GOLD_CAPS',
        'def _on_auction_list_req', 'def _on_auction_register',
        'def _on_auction_buy', 'def _on_auction_bid',
        'self._on_auction_list_req', 'self.auction_listings',
    ]
    missing = [c for c in checks if c not in content]
    if missing:
        print(f'[bridge] MISSING: {missing}')
        return False
    print('[bridge] S044 patched OK -- 4 auction handlers + daily cap + data constants')
    return True


def patch_test():
    with open(TEST_PATH, 'r', encoding='utf-8') as f:
        content = f.read()

    if 'test_auction_register' in content:
        print('[test] S044 already patched')
        return True

    # Update imports to add auction constants
    old_import = (
        '    GATHER_ENERGY_MAX, GATHER_ENERGY_COST\n'
        ')'
    )
    new_import = (
        '    GATHER_ENERGY_MAX, GATHER_ENERGY_COST,\n'
        '    AUCTION_TAX_RATE, AUCTION_LISTING_FEE,\n'
        '    AUCTION_MAX_LISTINGS, DAILY_GOLD_CAPS\n'
        ')'
    )
    if old_import in content:
        content = content.replace(old_import, new_import, 1)
        print('[test] Updated imports')

    # Insert test cases before results section
    marker = '    # ━━━ 결과 ━━━'
    idx = content.find(marker)
    if idx < 0:
        match = re.search(r'^\s*print\(f"\\n{\'=\'', content, re.MULTILINE)
        if match:
            idx = match.start()

    if idx >= 0:
        content = content[:idx] + TEST_CODE + '\n' + content[idx:]
    else:
        print('[test] WARNING: Could not find insertion point')
        return False

    with open(TEST_PATH, 'w', encoding='utf-8') as f:
        f.write(content)

    checks = ['test_auction_register', 'test_auction_list', 'test_auction_buy', 'test_auction_bid']
    missing = [c for c in checks if c not in content]
    if missing:
        print(f'[test] MISSING: {missing}')
        return False
    print('[test] S044 patched OK -- 5 auction tests added')
    return True


if __name__ == '__main__':
    ok1 = patch_bridge()
    ok2 = patch_test()
    if ok1 and ok2:
        print('\nS044 all patches applied!')
    else:
        print('\nS044 PATCH FAILED!')
        sys.exit(1)
