// ━━━ NetworkManager.cs ━━━
// Unity MonoBehaviour로 작동하는 네트워크 매니저
// Gate → Field 연결 + 로그인 + 게임 진입 전체 파이프라인
// 수신 패킷을 Update()에서 처리 (메인 스레드 보장)

using System;
using System.Collections.Generic;
using UnityEngine;

namespace Network
{
    public class NetworkManager : MonoBehaviour
    {
        // ━━━ 설정 ━━━
        [Header("Server Settings")]
        public string GateHost = "127.0.0.1";
        public int GatePort = 8888;

        // ━━━ 상태 ━━━
        public enum ConnectionState
        {
            Disconnected,
            ConnectingGate,
            ConnectingField,
            LoggingIn,
            CharSelect,
            InGame,
        }

        public ConnectionState State { get; private set; } = ConnectionState.Disconnected;
        public ulong MyEntityId { get; private set; }
        public int CurrentZone { get; private set; }
        public int CurrentChannel { get; private set; }

        // ━━━ TCP 클라이언트 ━━━
        private TCPClient _gate;
        private TCPClient _field;

        // 현재 활성 연결
        private TCPClient ActiveClient => _field ?? _gate;

        // ━━━ 이벤트 (UI/게임 로직이 구독) ━━━
        public event Action<LoginResult, uint> OnLoginResult;
        public event Action<CharacterInfo[]> OnCharacterList;
        public event Action<EnterGameResult> OnEnterGame;
        public event Action<ulong, float, float, float> OnEntityAppear;
        public event Action<ulong> OnEntityDisappear;
        public event Action<ulong, float, float, float> OnEntityMove;
        public event Action<int> OnZoneChanged;
        public event Action<int> OnChannelChanged;
        public event Action<StatSyncData> OnStatSync;
        public event Action<AttackResultData> OnAttackResult;
        public event Action<CombatDiedData> OnCombatDied;
        public event Action<RespawnResultData> OnRespawnResult;
        public event Action<MonsterSpawnData> OnMonsterSpawn;
        public event Action<MonsterRespawnData> OnMonsterRespawn;
        public event Action<ZoneTransferResultData> OnZoneTransferResult;
        public event Action<SkillInfo[]> OnSkillList;
        public event Action<SkillResultData> OnSkillResult;
        public event Action<PartyInfoData> OnPartyInfo;
        public event Action<InstanceEnterData> OnInstanceEnter;
        public event Action<InstanceLeaveResultData> OnInstanceLeaveResult;
        public event Action<InstanceInfoData> OnInstanceInfo;
        public event Action<MatchFoundData> OnMatchFound;
        public event Action<MatchStatusData> OnMatchStatus;
        public event Action<InventoryItemInfo[]> OnInventoryResp;
        public event Action<ItemAddResultData> OnItemAddResult;
        public event Action<ItemUseResultData> OnItemUseResult;
        public event Action<ItemEquipResultData> OnItemEquipResult;
        public event Action<BuffInfo[]> OnBuffList;
        public event Action<BuffResultData> OnBuffResult;
        public event Action<BuffRemoveRespData> OnBuffRemoveResp;
        public event Action<byte> OnConditionResult;
        public event Action<SpatialQueryEntry[]> OnSpatialQueryResp;
        public event Action<LootItemEntry[]> OnLootResult;
        public event Action<QuestInfo[]> OnQuestList;
        public event Action<QuestAcceptResultData> OnQuestAcceptResult;
        public event Action<QuestCompleteResultData> OnQuestCompleteResult;
        // 세션 35: 이동 검증
        public event Action<float, float, float> OnPositionCorrection;
        // 세션 30: 채팅
        public event Action<ChatMessageData> OnChatMessage;
        public event Action<WhisperResultData> OnWhisperResult;
        public event Action<string> OnSystemMessage;
        // 세션 32: 상점
        public event Action<ShopListData> OnShopList;
        public event Action<ShopResultData> OnShopResult;
        // 세션 33: 스킬 확장
        public event Action<SkillLevelUpResultData> OnSkillLevelUpResult;
        public event Action<SkillPointInfoData> OnSkillPointInfo;
        // 세션 34: 보스
        public event Action<BossSpawnData> OnBossSpawn;
        public event Action<BossPhaseChangeData> OnBossPhaseChange;
        public event Action<BossSpecialAttackData> OnBossSpecialAttack;
        public event Action<BossEnrageData> OnBossEnrage;
        public event Action<BossDefeatedData> OnBossDefeated;
        // 세션 36: 몬스터 AI
        public event Action<MonsterMoveData> OnMonsterMove;
        public event Action<MonsterAggroData> OnMonsterAggro;
        // 세션 37: 어드민
        public event Action<AdminReloadResultData> OnAdminReloadResult;
        public event Action<AdminConfigRespData> OnAdminConfigResp;
        // S033: 서버 선택 / 캐릭터 CRUD / 튜토리얼
        public event Action<ServerInfo[]> OnServerList;
        public event Action<CharacterData[]> OnCharacterDataList;
        public event Action<CharacterCreateResultData> OnCharacterCreateResult;
        public event Action<CharacterDeleteResultData> OnCharacterDeleteResult;
        public event Action<TutorialRewardData> OnTutorialReward;
        // S034: NPC / 강화
        public event Action<NpcDialogData> OnNpcDialog;
        public event Action<EnhanceResultData> OnEnhanceResult;
        // S029: 문파 / 거래 / 우편
        public event Action<GuildInfoData> OnGuildInfo;
        public event Action<GuildListEntry[]> OnGuildList;
        public event Action<TradeResultData> OnTradeResult;
        public event Action<MailListEntry[]> OnMailList;
        public event Action<MailReadData> OnMailRead;
        public event Action<MailClaimResultData> OnMailClaimResult;
        public event Action<MailDeleteResultData> OnMailDeleteResult;
        // S036: PvP 아레나
        public event Action<PvPQueueStatusData> OnPvPQueueStatus;
        public event Action<PvPMatchFoundData> OnPvPMatchFound;
        public event Action<PvPMatchStartData> OnPvPMatchStart;
        public event Action<PvPAttackResultData> OnPvPAttackResult;
        public event Action<PvPMatchEndData> OnPvPMatchEnd;
        public event Action<PvPRatingInfoData> OnPvPRatingInfo;
        // S036: 레이드 보스
        public event Action<RaidBossSpawnData> OnRaidBossSpawn;
        public event Action<RaidPhaseChangeData> OnRaidPhaseChange;
        public event Action<RaidMechanicData> OnRaidMechanic;
        public event Action<RaidMechanicResultData> OnRaidMechanicResult;
        public event Action<RaidStaggerData> OnRaidStagger;
        public event Action<uint> OnRaidEnrage;
        public event Action<RaidWipeData> OnRaidWipe;
        public event Action<RaidClearData> OnRaidClear;
        public event Action<RaidAttackResultData> OnRaidAttackResult;
        // S045: 거래소
        public event Action<AuctionListData> OnAuctionList;
        public event Action<AuctionRegisterResultData> OnAuctionRegisterResult;
        public event Action<AuctionBuyResultData> OnAuctionBuyResult;
        public event Action<AuctionBidResultData> OnAuctionBidResult;
        // S041: 제작/채집/요리/인챈트/보석
        public event Action<CraftRecipeInfo[]> OnCraftList;
        public event Action<CraftResultData> OnCraftResult;
        public event Action<GatherResultData> OnGatherResult;
        public event Action<CookResultData> OnCookResult;
        public event Action<EnchantResultData> OnEnchantResultResp;
        public event Action<GemEquipResultData> OnGemEquipResult;
        public event Action<GemFuseResultData> OnGemFuseResult;
        // S042: 캐시샵/배틀패스/이벤트
        public event Action<CashShopItemInfo[]> OnCashShopList;
        public event Action<CashShopBuyResultData> OnCashShopBuyResult;
        public event Action<BattlePassInfoData> OnBattlePassInfo;
        public event Action<BattlePassRewardResultData> OnBattlePassRewardResult;
        public event Action<BattlePassBuyResultData> OnBattlePassBuyResult;
        public event Action<GameEventInfo[]> OnEventList;
        public event Action<EventClaimResultData> OnEventClaimResult;
        public event Action<SubscriptionInfoData> OnSubscriptionInfo;
        // S042: 월드 시스템
        public event Action<WeatherUpdateData> OnWeatherUpdate;
        public event Action<uint> OnTimeUpdate;
        public event Action<WaypointInfo[]> OnTeleportList;
        public event Action<TeleportResultData> OnTeleportResult;
        public event Action<WorldObjectResultData> OnWorldObjectResult;
        public event Action<MountResultData> OnMountResult;
        public event Action<byte> OnMountDismountResult;
        // S042: 출석/리셋/컨텐츠 해금
        public event Action<AttendanceInfoData> OnAttendanceInfo;
        public event Action<AttendanceClaimResultData> OnAttendanceClaimResult;
        public event Action<DailyResetNotifyData> OnDailyResetNotify;
        public event Action<ContentUnlockNotifyData> OnContentUnlockNotify;
        public event Action<LoginRewardNotifyData> OnLoginRewardNotify;
        // S042: 스토리/대화 시스템
        public event Action<DialogChoiceResultData> OnDialogChoiceResult;
        public event Action<CutsceneTriggerData> OnCutsceneTrigger;
        public event Action<ushort> OnCutsceneEnd;
        public event Action<StoryProgressData> OnStoryProgress;
        public event Action<MainQuestDataInfo> OnMainQuestData;
        // S046: 비급 & 트라이포드
        public event Action<TripodListData> OnTripodList;
        public event Action<TripodEquipResult> OnTripodEquipResult;
        public event Action<ScrollDiscoverResultData> OnScrollDiscoverResult;
        // S047: 현상금 시스템
        public event Action<BountyListData> OnBountyList;
        public event Action<BountyAcceptResultData> OnBountyAcceptResult;
        public event Action<BountyCompleteData> OnBountyComplete;
        public event Action<BountyRankingData> OnBountyRanking;
        public event Action<PvPBountyNotifyData> OnPvPBountyNotify;
        // S048: 퀘스트 심화 (TASK 4)
        public event Action<DailyQuestListData> OnDailyQuestList;
        public event Action<WeeklyQuestData> OnWeeklyQuest;
        public event Action<ReputationInfoData> OnReputationInfo;
        // S049: 칭호/도감/2차전직 (TASK 7)
        public event Action<TitleListData> OnTitleList;
        public event Action<TitleEquipResultData> OnTitleEquipResult;
        public event Action<CollectionInfoData> OnCollectionInfo;
        public event Action<JobChangeResultData> OnJobChangeResult;
        // S050: 각인/초월
        public event Action<EngravingListData> OnEngravingList;
        public event Action<EngravingResultData> OnEngravingResult;
        public event Action<TranscendResultData> OnTranscendResult;
        // S051: 소셜 심화
        public event Action<FriendRequestResult> OnFriendRequestResult;
        public event Action<FriendListData> OnFriendList;
        public event Action<BlockPlayerResult> OnBlockResult;
        public event Action<BlockListData> OnBlockList;
        public event Action<PartyFinderListData> OnPartyFinderList;
        // S052: 내구도/수리/리롤
        public event Action<RepairResultData> OnRepairResult;
        public event Action<RerollResultData> OnRerollResult;
        public event Action<DurabilityNotifyData> OnDurabilityNotify;
        // S053: 전장/길드전/PvP시즌
        public event Action<BattlegroundStatusData> OnBattlegroundStatus;
        public event Action<BattlegroundScoreUpdateData> OnBattlegroundScoreUpdate;
        public event Action<GuildWarStatusData> OnGuildWarStatus;
        // S054: 보조 화폐/토큰 상점
        public event Action<CurrencyInfoData> OnCurrencyInfo;
        public event Action<TokenShopData> OnTokenShop;
        public event Action<TokenShopBuyResultData> OnTokenShopBuyResult;
        // 공통
        public event Action<string> OnError;
        public event Action OnDisconnected;

        // ━━━ 싱글톤 ━━━
        public static NetworkManager Instance { get; private set; }

        private void Awake()
        {
            if (Instance != null && Instance != this)
            {
                Destroy(gameObject);
                return;
            }
            Instance = this;
            DontDestroyOnLoad(gameObject);
        }

        private void OnDestroy()
        {
            _gate?.Dispose();
            _field?.Dispose();
            if (Instance == this) Instance = null;
        }

        // ━━━ Update: 수신 패킷 처리 (메인 스레드) ━━━

        private void Update()
        {
            _gate?.DequeueAll(HandleGatePacket);
            _field?.DequeueAll(HandleFieldPacket);
        }

        // ━━━ 공개 API ━━━

        /// <summary>1단계: Gate 서버 연결 → 자동으로 GATE_ROUTE_REQ 전송</summary>
        public void ConnectToGate()
        {
            State = ConnectionState.ConnectingGate;
            _gate = new TCPClient();
            _gate.OnDisconnected += () => { /* Gate는 1회용이라 무시 */ };

            if (!_gate.Connect(GateHost, GatePort))
            {
                OnError?.Invoke("Gate 서버 연결 실패");
                State = ConnectionState.Disconnected;
                return;
            }

            Debug.Log($"[Net] Gate 연결 성공 ({GateHost}:{GatePort})");
            _gate.Send(PacketBuilder.GateRouteReq());
        }

        /// <summary>3단계: 로그인</summary>
        public void Login(string username, string password)
        {
            if (_field == null || !_field.IsConnected)
            {
                OnError?.Invoke("Field 서버에 연결되지 않음");
                return;
            }

            State = ConnectionState.LoggingIn;
            _field.Send(PacketBuilder.Login(username, password));
        }

        /// <summary>4단계: 캐릭터 목록 요청</summary>
        public void RequestCharList()
        {
            _field?.Send(PacketBuilder.CharListReq());
        }

        /// <summary>5단계: 캐릭터 선택</summary>
        public void SelectCharacter(uint charId)
        {
            State = ConnectionState.CharSelect;
            _field?.Send(PacketBuilder.CharSelect(charId));
        }

        /// <summary>6단계: 채널 입장</summary>
        public void JoinChannel(int channelId)
        {
            CurrentChannel = channelId;
            _field?.Send(PacketBuilder.ChannelJoin(channelId));
        }

        /// <summary>이동 전송 (Model C: timestamp 포함)</summary>
        public void SendMove(float x, float y, float z, uint timestampMs = 0)
        {
            _field?.Send(PacketBuilder.Move(x, y, z, timestampMs));
        }

        /// <summary>존 이동</summary>
        public void EnterZone(int zoneId)
        {
            _field?.Send(PacketBuilder.ZoneEnter(zoneId));
        }

        /// <summary>스탯 동기화 요청</summary>
        public void RequestStatSync()
        {
            _field?.Send(PacketBuilder.StatQuery());
        }

        /// <summary>공격 요청</summary>
        public void SendAttack(ulong targetEntityId)
        {
            _field?.Send(PacketBuilder.AttackReq(targetEntityId));
        }

        /// <summary>부활 요청</summary>
        public void RequestRespawn()
        {
            _field?.Send(PacketBuilder.RespawnReq());
        }

        /// <summary>Gate 없이 Field 서버에 직접 연결</summary>
        public void ConnectDirect(string host, int port)
        {
            ConnectToField(host, port);
        }

        // ━━━ 세션 16~28 API ━━━

        /// <summary>존 이동 요청</summary>
        public void RequestZoneTransfer(int targetZoneId)
        {
            _field?.Send(PacketBuilder.ZoneTransferReq(targetZoneId));
        }

        /// <summary>스킬 목록 요청</summary>
        public void RequestSkillList()
        {
            _field?.Send(PacketBuilder.SkillListReq());
        }

        /// <summary>스킬 사용</summary>
        public void UseSkill(uint skillId, ulong targetEntity)
        {
            _field?.Send(PacketBuilder.SkillUse(skillId, targetEntity));
        }

        /// <summary>파티 생성</summary>
        public void CreateParty()
        {
            _field?.Send(PacketBuilder.PartyCreate());
        }

        /// <summary>파티 초대</summary>
        public void InviteToParty(ulong targetEntity)
        {
            _field?.Send(PacketBuilder.PartyInvite(targetEntity));
        }

        /// <summary>파티 수락</summary>
        public void AcceptParty(uint partyId)
        {
            _field?.Send(PacketBuilder.PartyAccept(partyId));
        }

        /// <summary>파티 탈퇴</summary>
        public void LeaveParty()
        {
            _field?.Send(PacketBuilder.PartyLeave());
        }

        /// <summary>파티 추방</summary>
        public void KickFromParty(ulong targetEntity)
        {
            _field?.Send(PacketBuilder.PartyKick(targetEntity));
        }

        /// <summary>인스턴스 던전 생성</summary>
        public void CreateInstance(uint dungeonType)
        {
            _field?.Send(PacketBuilder.InstanceCreate(dungeonType));
        }

        /// <summary>인스턴스 퇴장</summary>
        public void LeaveInstance()
        {
            _field?.Send(PacketBuilder.InstanceLeave());
        }

        /// <summary>매칭 큐 등록</summary>
        public void EnqueueMatch(uint dungeonType)
        {
            _field?.Send(PacketBuilder.MatchEnqueue(dungeonType));
        }

        /// <summary>매칭 큐 해제</summary>
        public void DequeueMatch()
        {
            _field?.Send(PacketBuilder.MatchDequeue());
        }

        /// <summary>매칭 수락</summary>
        public void AcceptMatch(uint matchId)
        {
            _field?.Send(PacketBuilder.MatchAccept(matchId));
        }

        /// <summary>인벤토리 요청</summary>
        public void RequestInventory()
        {
            _field?.Send(PacketBuilder.InventoryReq());
        }

        /// <summary>아이템 사용</summary>
        public void UseItem(byte slot)
        {
            _field?.Send(PacketBuilder.ItemUse(slot));
        }

        /// <summary>아이템 장착</summary>
        public void EquipItem(byte slot)
        {
            _field?.Send(PacketBuilder.ItemEquip(slot));
        }

        /// <summary>아이템 해제</summary>
        public void UnequipItem(byte slot)
        {
            _field?.Send(PacketBuilder.ItemUnequip(slot));
        }

        /// <summary>버프 목록 요청</summary>
        public void RequestBuffList()
        {
            _field?.Send(PacketBuilder.BuffListReq());
        }

        /// <summary>버프 적용 요청</summary>
        public void ApplyBuff(uint buffId)
        {
            _field?.Send(PacketBuilder.BuffApplyReq(buffId));
        }

        /// <summary>버프 제거 요청</summary>
        public void RemoveBuff(uint buffId)
        {
            _field?.Send(PacketBuilder.BuffRemoveReq(buffId));
        }

        /// <summary>루트 굴림 요청</summary>
        public void RequestLootRoll(uint tableId)
        {
            _field?.Send(PacketBuilder.LootRollReq(tableId));
        }

        /// <summary>퀘스트 목록 요청</summary>
        public void RequestQuestList()
        {
            _field?.Send(PacketBuilder.QuestListReq());
        }

        /// <summary>퀘스트 수락</summary>
        public void AcceptQuest(uint questId)
        {
            _field?.Send(PacketBuilder.QuestAccept(questId));
        }

        /// <summary>퀘스트 진행 확인</summary>
        public void CheckQuestProgress(uint questId)
        {
            _field?.Send(PacketBuilder.QuestProgress(questId));
        }

        /// <summary>퀘스트 완료</summary>
        public void CompleteQuest(uint questId)
        {
            _field?.Send(PacketBuilder.QuestComplete(questId));
        }

        // ━━━ 세션 30: 채팅 API ━━━

        /// <summary>채팅 메시지 전송</summary>
        public void SendChat(ChatChannel channel, string message)
        {
            _field?.Send(PacketBuilder.ChatSend(channel, message));
        }

        /// <summary>귓속말 전송</summary>
        public void SendWhisper(string targetName, string message)
        {
            _field?.Send(PacketBuilder.WhisperSend(targetName, message));
        }

        // ━━━ 세션 32: 상점 API ━━━

        /// <summary>상점 열기</summary>
        public void OpenShop(uint npcId)
        {
            _field?.Send(PacketBuilder.ShopOpen(npcId));
        }

        /// <summary>상점 구매</summary>
        public void ShopBuy(uint npcId, uint itemId, ushort count)
        {
            _field?.Send(PacketBuilder.ShopBuy(npcId, itemId, count));
        }

        /// <summary>상점 판매</summary>
        public void ShopSell(byte slot, ushort count)
        {
            _field?.Send(PacketBuilder.ShopSell(slot, count));
        }

        // ━━━ 세션 33: 스킬 레벨업 API ━━━

        /// <summary>스킬 레벨업</summary>
        public void SkillLevelUp(uint skillId)
        {
            _field?.Send(PacketBuilder.SkillLevelUp(skillId));
        }

        // ━━━ 세션 37: 어드민 API ━━━

        /// <summary>설정 리로드 요청</summary>
        public void AdminReload(string configName = "")
        {
            _field?.Send(PacketBuilder.AdminReload(configName));
        }

        /// <summary>설정값 조회</summary>
        public void AdminGetConfig(string configName, string key)
        {
            _field?.Send(PacketBuilder.AdminGetConfig(configName, key));
        }

        // ━━━ S033: 서버 선택 / 캐릭터 CRUD / 튜토리얼 API ━━━

        /// <summary>서버 목록 요청</summary>
        public void RequestServerList()
        {
            _field?.Send(PacketBuilder.ServerListReq());
        }

        /// <summary>캐릭터 목록 요청 (실제 생성된 캐릭터)</summary>
        public void RequestCharacterList()
        {
            _field?.Send(PacketBuilder.CharacterListReq());
        }

        /// <summary>캐릭터 생성</summary>
        public void CreateCharacter(string name, CharacterClass classType)
        {
            _field?.Send(PacketBuilder.CharacterCreate(name, classType));
        }

        /// <summary>캐릭터 삭제</summary>
        public void DeleteCharacter(uint charId)
        {
            _field?.Send(PacketBuilder.CharacterDelete(charId));
        }

        /// <summary>튜토리얼 스텝 완료</summary>
        public void CompleteTutorialStep(byte stepId)
        {
            _field?.Send(PacketBuilder.TutorialStepComplete(stepId));
        }

        // ━━━ S034: NPC / 강화 API ━━━

        /// <summary>NPC 인터랙션 (F키)</summary>
        public void InteractNpc(uint npcEntityId)
        {
            _field?.Send(PacketBuilder.NpcInteract(npcEntityId));
        }

        /// <summary>강화 요청</summary>
        public void RequestEnhance(byte slotIndex)
        {
            _field?.Send(PacketBuilder.EnhanceReq(slotIndex));
        }

        // ━━━ S029: 문파 API ━━━

        /// <summary>문파 생성</summary>
        public void CreateGuild(string guildName)
        {
            _field?.Send(PacketBuilder.GuildCreate(guildName));
        }

        /// <summary>문파 해산</summary>
        public void DisbandGuild()
        {
            _field?.Send(PacketBuilder.GuildDisband());
        }

        /// <summary>문파 초대</summary>
        public void InviteToGuild(ulong targetEntity)
        {
            _field?.Send(PacketBuilder.GuildInvite(targetEntity));
        }

        /// <summary>문파 초대 수락</summary>
        public void AcceptGuildInvite()
        {
            _field?.Send(PacketBuilder.GuildAccept());
        }

        /// <summary>문파 탈퇴</summary>
        public void LeaveGuild()
        {
            _field?.Send(PacketBuilder.GuildLeave());
        }

        /// <summary>문파 추방</summary>
        public void KickFromGuild(ulong targetEntity)
        {
            _field?.Send(PacketBuilder.GuildKick(targetEntity));
        }

        /// <summary>문파 정보 요청</summary>
        public void RequestGuildInfo()
        {
            _field?.Send(PacketBuilder.GuildInfoReq());
        }

        /// <summary>문파 목록 요청</summary>
        public void RequestGuildList()
        {
            _field?.Send(PacketBuilder.GuildListReq());
        }

        // ━━━ S029: 거래 API ━━━

        /// <summary>거래 요청</summary>
        public void RequestTrade(ulong targetEntity)
        {
            _field?.Send(PacketBuilder.TradeRequest(targetEntity));
        }

        /// <summary>거래 수락</summary>
        public void AcceptTrade()
        {
            _field?.Send(PacketBuilder.TradeAccept());
        }

        /// <summary>거래 거절</summary>
        public void DeclineTrade()
        {
            _field?.Send(PacketBuilder.TradeDecline());
        }

        /// <summary>거래 아이템 추가</summary>
        public void TradeAddItem(byte slotIndex)
        {
            _field?.Send(PacketBuilder.TradeAddItem(slotIndex));
        }

        /// <summary>거래 골드 추가</summary>
        public void TradeAddGold(uint amount)
        {
            _field?.Send(PacketBuilder.TradeAddGold(amount));
        }

        /// <summary>거래 확정</summary>
        public void ConfirmTrade()
        {
            _field?.Send(PacketBuilder.TradeConfirm());
        }

        /// <summary>거래 취소</summary>
        public void CancelTrade()
        {
            _field?.Send(PacketBuilder.TradeCancel());
        }

        // ━━━ S029: 우편 API ━━━

        /// <summary>우편 발송</summary>
        public void SendMail(string recipient, string title, string body, uint gold = 0, uint itemId = 0, ushort itemCount = 0)
        {
            _field?.Send(PacketBuilder.MailSend(recipient, title, body, gold, itemId, itemCount));
        }

        /// <summary>우편함 목록 요청</summary>
        public void RequestMailList()
        {
            _field?.Send(PacketBuilder.MailListReq());
        }

        /// <summary>우편 읽기</summary>
        public void ReadMail(uint mailId)
        {
            _field?.Send(PacketBuilder.MailRead(mailId));
        }

        /// <summary>우편 첨부물 수령</summary>
        public void ClaimMail(uint mailId)
        {
            _field?.Send(PacketBuilder.MailClaim(mailId));
        }

        /// <summary>우편 삭제</summary>
        public void DeleteMail(uint mailId)
        {
            _field?.Send(PacketBuilder.MailDelete(mailId));
        }

        // ━━━ S036: PvP 아레나 API ━━━

        /// <summary>PvP 큐 등록 (mode: 1=1v1, 2=3v3)</summary>
        public void PvPQueueReq(byte mode)
        {
            _field?.Send(PacketBuilder.PvPQueueReq(mode));
        }

        /// <summary>PvP 큐 취소</summary>
        public void PvPQueueCancel()
        {
            _field?.Send(PacketBuilder.PvPQueueCancel());
        }

        /// <summary>PvP 매치 수락</summary>
        public void PvPMatchAccept(uint matchId)
        {
            _field?.Send(PacketBuilder.PvPMatchAccept(matchId));
        }

        /// <summary>PvP 공격</summary>
        public void PvPAttack(uint matchId, byte targetTeam, byte targetIdx, ushort skillId, ushort damage)
        {
            _field?.Send(PacketBuilder.PvPAttack(matchId, targetTeam, targetIdx, skillId, damage));
        }

        // ━━━ S036: 레이드 API ━━━

        /// <summary>레이드 보스 공격</summary>
        public void RaidAttack(uint instanceId, ushort skillId, uint damage)
        {
            _field?.Send(PacketBuilder.RaidAttack(instanceId, skillId, damage));
        }

        // ━━━ S045: 거래소 API ━━━

        /// <summary>거래소 목록 요청</summary>
        public void RequestAuctionList(byte category, byte page, byte sortBy)
        {
            _field?.Send(PacketBuilder.AuctionListReq(category, page, sortBy));
        }

        /// <summary>거래소 아이템 등록</summary>
        public void RegisterAuction(byte slotIdx, byte count, uint buyoutPrice, byte category)
        {
            _field?.Send(PacketBuilder.AuctionRegister(slotIdx, count, buyoutPrice, category));
        }

        /// <summary>거래소 즉시 구매</summary>
        public void BuyAuction(uint auctionId)
        {
            _field?.Send(PacketBuilder.AuctionBuy(auctionId));
        }

        /// <summary>거래소 입찰</summary>
        public void BidAuction(uint auctionId, uint bidAmount)
        {
            _field?.Send(PacketBuilder.AuctionBid(auctionId, bidAmount));
        }

        // ━━━ S043: 제작/채집/요리/인챈트/보석 API ━━━

        /// <summary>제작 레시피 목록 요청 (카테고리 필터)</summary>
        public void RequestCraftList(byte category = 0xFF)
        {
            _field?.Send(PacketBuilder.CraftListReq(category));
        }

        /// <summary>제작 실행 (문자열 recipe_id)</summary>
        public void ExecuteCraft(string recipeId)
        {
            _field?.Send(PacketBuilder.CraftExecute(recipeId));
        }

        /// <summary>채집 시작</summary>
        public void StartGather(byte gatherType)
        {
            _field?.Send(PacketBuilder.GatherStart(gatherType));
        }

        /// <summary>요리 실행 (문자열 recipe_id)</summary>
        public void ExecuteCook(string recipeId)
        {
            _field?.Send(PacketBuilder.CookExecute(recipeId));
        }

        /// <summary>인챈트 요청</summary>
        public void RequestEnchant(byte slot, byte element, byte level)
        {
            _field?.Send(PacketBuilder.EnchantReq(slot, element, level));
        }

        /// <summary>보석 장착</summary>
        public void EquipGem(byte itemSlot, byte gemSlot, uint gemItemId)
        {
            _field?.Send(PacketBuilder.GemEquip(itemSlot, gemSlot, gemItemId));
        }

        /// <summary>보석 합성</summary>
        public void FuseGem(byte gemType, byte gemTier)
        {
            _field?.Send(PacketBuilder.GemFuse(gemType, gemTier));
        }

        // ━━━ S042: 캐시샵/배틀패스/이벤트 API ━━━

        /// <summary>캐시샵 목록 요청</summary>
        public void RequestCashShopList(byte category)
        {
            _field?.Send(PacketBuilder.CashShopListReq(category));
        }

        /// <summary>캐시샵 구매</summary>
        public void BuyCashShopItem(uint itemId, byte count = 1)
        {
            _field?.Send(PacketBuilder.CashShopBuy(itemId, count));
        }

        /// <summary>배틀패스 정보 요청</summary>
        public void RequestBattlePassInfo()
        {
            _field?.Send(PacketBuilder.BattlePassInfoReq());
        }

        /// <summary>배틀패스 보상 수령</summary>
        public void ClaimBattlePassReward(byte level, byte track)
        {
            _field?.Send(PacketBuilder.BattlePassRewardClaim(level, track));
        }

        /// <summary>배틀패스 프리미엄 구매</summary>
        public void BuyBattlePassPremium()
        {
            _field?.Send(PacketBuilder.BattlePassBuyPremium());
        }

        /// <summary>이벤트 목록 요청</summary>
        public void RequestEventList()
        {
            _field?.Send(PacketBuilder.EventListReq());
        }

        /// <summary>이벤트 보상 수령</summary>
        public void ClaimEventReward(ushort eventId)
        {
            _field?.Send(PacketBuilder.EventClaim(eventId));
        }

        /// <summary>월정액 정보 요청</summary>
        public void RequestSubscriptionInfo()
        {
            _field?.Send(PacketBuilder.SubscriptionInfoReq());
        }

        // ━━━ S042: 월드 시스템 API ━━━

        /// <summary>텔레포트 목록 요청</summary>
        public void RequestTeleportList()
        {
            _field?.Send(PacketBuilder.TeleportListReq());
        }

        /// <summary>텔레포트 요청</summary>
        public void RequestTeleport(ushort waypointId)
        {
            _field?.Send(PacketBuilder.TeleportReq(waypointId));
        }

        /// <summary>월드 오브젝트 상호작용</summary>
        public void InteractWorldObject(uint objectId, byte action)
        {
            _field?.Send(PacketBuilder.WorldObjectInteract(objectId, action));
        }

        /// <summary>탈것 소환</summary>
        public void SummonMount(uint mountId)
        {
            _field?.Send(PacketBuilder.MountSummon(mountId));
        }

        /// <summary>탈것 내리기</summary>
        public void DismountMount()
        {
            _field?.Send(PacketBuilder.MountDismount());
        }

        // ━━━ S042: 출석/컨텐츠 해금 API ━━━

        /// <summary>출석 정보 요청</summary>
        public void RequestAttendanceInfo()
        {
            _field?.Send(PacketBuilder.AttendanceInfoReq());
        }

        /// <summary>출석 보상 수령</summary>
        public void ClaimAttendance(byte day)
        {
            _field?.Send(PacketBuilder.AttendanceClaim(day));
        }

        /// <summary>컨텐츠 해금 확인 응답</summary>
        public void AckContentUnlock(byte unlockType)
        {
            _field?.Send(PacketBuilder.ContentUnlockAck(unlockType));
        }

        // ━━━ S042: 스토리/대화 API ━━━

        /// <summary>대화 선택지 선택</summary>
        public void SelectDialogChoice(ushort npcId, byte choiceIndex)
        {
            _field?.Send(PacketBuilder.DialogChoice(npcId, choiceIndex));
        }

        /// <summary>컷씬 스킵</summary>
        public void SkipCutscene(ushort cutsceneId)
        {
            _field?.Send(PacketBuilder.CutsceneSkip(cutsceneId));
        }

        /// <summary>스토리 진행 요청</summary>
        public void RequestStoryProgress()
        {
            _field?.Send(PacketBuilder.StoryProgressReq());
        }

        // ━━━ S046: 비급 & 트라이포드 API ━━━

        /// <summary>트라이포드 목록 요청</summary>
        public void RequestTripodList()
        {
            _field?.Send(PacketBuilder.TripodListReq());
        }

        /// <summary>트라이포드 장착 요청</summary>
        public void RequestTripodEquip(ushort skillId, byte tier, byte optionIdx)
        {
            _field?.Send(PacketBuilder.TripodEquip(skillId, tier, optionIdx));
        }

        /// <summary>비급 사용 (인벤토리 비급 아이템 → 트라이포드 해금)</summary>
        public void RequestScrollDiscover(byte scrollSlot)
        {
            _field?.Send(PacketBuilder.ScrollDiscover(scrollSlot));
        }

        // ━━━ S047: 현상금 시스템 API ━━━

        /// <summary>현상금 목록 요청</summary>
        public void RequestBountyList()
        {
            _field?.Send(PacketBuilder.BountyListReq());
        }

        /// <summary>현상금 수락</summary>
        public void AcceptBounty(ushort bountyId)
        {
            _field?.Send(PacketBuilder.BountyAccept(bountyId));
        }

        /// <summary>현상금 완료 요청</summary>
        public void CompleteBounty(ushort bountyId)
        {
            _field?.Send(PacketBuilder.BountyCompleteReq(bountyId));
        }

        /// <summary>현상금 랭킹 요청</summary>
        public void RequestBountyRanking()
        {
            _field?.Send(PacketBuilder.BountyRankingReq());
        }

        // ━━━ S048: 퀘스트 심화 API (TASK 4) ━━━

        /// <summary>일일 퀘스트 목록 요청</summary>
        public void RequestDailyQuestList()
        {
            _field?.Send(PacketBuilder.DailyQuestListReq());
        }

        /// <summary>주간 퀘스트 요청</summary>
        public void RequestWeeklyQuest()
        {
            _field?.Send(PacketBuilder.WeeklyQuestReq());
        }

        /// <summary>평판 조회 요청</summary>
        public void RequestReputation()
        {
            _field?.Send(PacketBuilder.ReputationQuery());
        }

        // ━━━ S049: 칭호/도감/2차전직 API (TASK 7) ━━━

        /// <summary>칭호 목록 요청</summary>
        public void RequestTitleList()
        {
            _field?.Send(PacketBuilder.TitleListReq());
        }

        /// <summary>칭호 장착/해제 (titleId=0이면 해제)</summary>
        public void EquipTitle(ushort titleId)
        {
            _field?.Send(PacketBuilder.TitleEquip(titleId));
        }

        /// <summary>도감 조회 요청</summary>
        public void RequestCollection()
        {
            _field?.Send(PacketBuilder.CollectionQuery());
        }

        /// <summary>2차 전직 요청</summary>
        public void RequestJobChange(string jobName)
        {
            _field?.Send(PacketBuilder.JobChangeReq(jobName));
        }

        // ━━━ S050: 각인/초월 API ━━━

        /// <summary>각인 목록 요청</summary>
        public void RequestEngravingList()
        {
            _field?.Send(PacketBuilder.EngravingListReq());
        }

        /// <summary>각인 활성화/비활성화 (action: 0=activate, 1=deactivate)</summary>
        public void EquipEngraving(byte action, string name)
        {
            _field?.Send(PacketBuilder.EngravingEquip(action, name));
        }

        /// <summary>장비 초월 요청</summary>
        public void RequestTranscend(string slot)
        {
            _field?.Send(PacketBuilder.TranscendReq(slot));
        }

        // ━━━ S051: 소셜 심화 API ━━━

        /// <summary>친구 요청</summary>
        public void RequestFriend(string targetName)
        {
            _field?.Send(PacketBuilder.FriendRequest(targetName));
        }

        /// <summary>친구 수락</summary>
        public void AcceptFriend(string fromName)
        {
            _field?.Send(PacketBuilder.FriendAccept(fromName));
        }

        /// <summary>친구 거절</summary>
        public void RejectFriend(string fromName)
        {
            _field?.Send(PacketBuilder.FriendReject(fromName));
        }

        /// <summary>친구 목록 요청</summary>
        public void RequestFriendList()
        {
            _field?.Send(PacketBuilder.FriendListReq());
        }

        /// <summary>차단/해제 (action: 0=block, 1=unblock)</summary>
        public void BlockPlayer(byte action, string name)
        {
            _field?.Send(PacketBuilder.BlockPlayer(action, name));
        }

        /// <summary>차단 목록 요청</summary>
        public void RequestBlockList()
        {
            _field?.Send(PacketBuilder.BlockListReq());
        }

        /// <summary>파티 찾기 목록 요청</summary>
        public void RequestPartyFinderList(byte category)
        {
            _field?.Send(PacketBuilder.PartyFinderListReq(category));
        }

        /// <summary>파티 찾기 등록</summary>
        public void CreatePartyFinderListing(string title, byte category, byte minLevel, byte role)
        {
            _field?.Send(PacketBuilder.PartyFinderCreate(title, category, minLevel, role));
        }

        // ━━━ S052: 내구도/수리/리롤 API ━━━

        /// <summary>장비 수리 요청 (mode: 0=단일, 1=전체)</summary>
        public void RequestRepair(byte mode, byte invSlot)
        {
            _field?.Send(PacketBuilder.RepairReq(mode, invSlot));
        }

        /// <summary>옵션 리롤 요청</summary>
        public void RequestReroll(byte invSlot, byte[] lockIndices)
        {
            _field?.Send(PacketBuilder.RerollReq(invSlot, lockIndices));
        }

        /// <summary>장착 장비 내구도 조회</summary>
        public void RequestDurabilityQuery()
        {
            _field?.Send(PacketBuilder.DurabilityQuery());
        }

        // ━━━ S053: 전장/길드전/PvP시즌 API ━━━

        /// <summary>전장 큐 등록 (action: 0=enqueue, 1=cancel; mode: 0=거점점령, 1=수레호위)</summary>
        public void BattlegroundQueue(byte action, byte mode)
        {
            _field?.Send(PacketBuilder.BattlegroundQueue(action, mode));
        }

        /// <summary>전장 점수 조회</summary>
        public void BattlegroundScoreQuery(byte action, byte pointIndex)
        {
            _field?.Send(PacketBuilder.BattlegroundScore(action, pointIndex));
        }

        /// <summary>길드전 선언/수락/거절/조회</summary>
        public void GuildWarAction(byte action, uint targetGuildId)
        {
            _field?.Send(PacketBuilder.GuildWarDeclare(action, targetGuildId));
        }

        // ━━━ S054: 보조 화폐/토큰 상점 API ━━━

        /// <summary>전체 화폐 조회</summary>
        public void RequestCurrencyQuery()
        {
            _field?.Send(PacketBuilder.CurrencyQuery());
        }

        /// <summary>토큰 상점 목록 요청 (shopType: 0=던전, 1=PvP, 2=길드)</summary>
        public void RequestTokenShopList(byte shopType)
        {
            _field?.Send(PacketBuilder.TokenShopList(shopType));
        }

        /// <summary>토큰 상점 구매</summary>
        public void RequestTokenShopBuy(ushort shopId, byte quantity)
        {
            _field?.Send(PacketBuilder.TokenShopBuy(shopId, quantity));
        }

        /// <summary>연결 끊기</summary>
        public void DisconnectAll()
        {
            _gate?.Dispose();
            _field?.Dispose();
            _gate = null;
            _field = null;
            State = ConnectionState.Disconnected;
        }

        // ━━━ Gate 패킷 핸들러 ━━━

        private void HandleGatePacket(MsgType type, byte[] payload)
        {
            if (type == MsgType.GATE_ROUTE_RESP)
            {
                var route = PacketBuilder.ParseGateRouteResp(payload);
                if (route.ResultCode != 0)
                {
                    OnError?.Invoke("Gate 라우팅 실패");
                    State = ConnectionState.Disconnected;
                    return;
                }

                Debug.Log($"[Net] Gate → Field {route.IP}:{route.Port}");

                // Gate 연결 닫기
                _gate.Dispose();
                _gate = null;

                // Field 연결
                ConnectToField(route.IP, route.Port);
            }
        }

        // ━━━ Field 연결 ━━━

        private void ConnectToField(string host, int port)
        {
            State = ConnectionState.ConnectingField;
            _field = new TCPClient();
            _field.OnDisconnected += () =>
            {
                State = ConnectionState.Disconnected;
                OnDisconnected?.Invoke();
            };

            if (!_field.Connect(host, port))
            {
                OnError?.Invoke($"Field 서버 연결 실패 ({host}:{port})");
                State = ConnectionState.Disconnected;
                return;
            }

            Debug.Log($"[Net] Field 연결 성공 ({host}:{port})");
            // 이제 Login() 호출 가능
            State = ConnectionState.ConnectingField; // Login 대기
        }

        // ━━━ Field 패킷 핸들러 ━━━

        private void HandleFieldPacket(MsgType type, byte[] payload)
        {
            switch (type)
            {
                case MsgType.LOGIN_RESULT:
                {
                    var (result, accountId) = PacketBuilder.ParseLoginResult(payload);
                    Debug.Log($"[Net] Login result: {result}, accountId: {accountId}");
                    OnLoginResult?.Invoke(result, accountId);
                    break;
                }

                case MsgType.CHAR_LIST_RESP:
                {
                    var chars = PacketBuilder.ParseCharListResp(payload);
                    Debug.Log($"[Net] Character list: {chars.Length} characters");
                    OnCharacterList?.Invoke(chars);
                    break;
                }

                case MsgType.ENTER_GAME:
                {
                    var r = PacketBuilder.ParseEnterGame(payload);
                    if (r.ResultCode == 0)
                    {
                        MyEntityId = r.EntityId;
                        CurrentZone = r.ZoneId;
                        State = ConnectionState.InGame;
                        Debug.Log($"[Net] Enter game: entity={r.EntityId}, zone={r.ZoneId}, pos=({r.X},{r.Y},{r.Z})");
                    }
                    OnEnterGame?.Invoke(r);
                    break;
                }

                case MsgType.APPEAR:
                {
                    var (eid, x, y, z) = PacketBuilder.ParseEntityPosition(payload);
                    if (eid != MyEntityId) // 자기 자신은 무시
                        OnEntityAppear?.Invoke(eid, x, y, z);
                    break;
                }

                case MsgType.DISAPPEAR:
                {
                    ulong eid = PacketBuilder.ParseDisappear(payload);
                    if (eid != MyEntityId)
                        OnEntityDisappear?.Invoke(eid);
                    break;
                }

                case MsgType.MOVE_BROADCAST:
                {
                    var (eid, x, y, z) = PacketBuilder.ParseEntityPosition(payload);
                    if (eid != MyEntityId)
                        OnEntityMove?.Invoke(eid, x, y, z);
                    break;
                }

                case MsgType.ZONE_INFO:
                {
                    int zoneId = PacketBuilder.ParseIntResponse(payload);
                    CurrentZone = zoneId;
                    Debug.Log($"[Net] Zone changed: {zoneId}");
                    OnZoneChanged?.Invoke(zoneId);
                    break;
                }

                case MsgType.CHANNEL_INFO:
                {
                    int chId = PacketBuilder.ParseIntResponse(payload);
                    CurrentChannel = chId;
                    Debug.Log($"[Net] Channel: {chId}");
                    OnChannelChanged?.Invoke(chId);
                    break;
                }

                case MsgType.STAT_SYNC:
                {
                    var data = PacketBuilder.ParseStatSync(payload);
                    Debug.Log($"[Net] StatSync: Lv{data.Level} HP={data.HP}/{data.MaxHP}");
                    OnStatSync?.Invoke(data);
                    break;
                }

                case MsgType.ATTACK_RESULT:
                {
                    var data = PacketBuilder.ParseAttackResult(payload);
                    Debug.Log($"[Net] AttackResult: {data.Result}, dmg={data.Damage}, target HP={data.TargetHP}/{data.TargetMaxHP}");
                    OnAttackResult?.Invoke(data);
                    break;
                }

                case MsgType.COMBAT_DIED:
                {
                    var data = PacketBuilder.ParseCombatDied(payload);
                    Debug.Log($"[Net] CombatDied: dead={data.DeadEntityId}, killer={data.KillerEntityId}");
                    OnCombatDied?.Invoke(data);
                    break;
                }

                case MsgType.RESPAWN_RESULT:
                {
                    var data = PacketBuilder.ParseRespawnResult(payload);
                    Debug.Log($"[Net] RespawnResult: result={data.ResultCode}, HP={data.HP}, pos=({data.X},{data.Y},{data.Z})");
                    OnRespawnResult?.Invoke(data);
                    break;
                }

                case MsgType.MONSTER_SPAWN:
                {
                    var data = PacketBuilder.ParseMonsterSpawn(payload);
                    Debug.Log($"[Net] MonsterSpawn: entity={data.EntityId}, monsterId={data.MonsterId}, lv={data.Level}, hp={data.HP}/{data.MaxHP}");
                    OnMonsterSpawn?.Invoke(data);
                    break;
                }

                case MsgType.MONSTER_RESPAWN:
                {
                    var data = PacketBuilder.ParseMonsterRespawn(payload);
                    Debug.Log($"[Net] MonsterRespawn: entity={data.EntityId}, hp={data.HP}/{data.MaxHP}");
                    OnMonsterRespawn?.Invoke(data);
                    break;
                }

                case MsgType.ZONE_TRANSFER_RESULT:
                {
                    var data = PacketBuilder.ParseZoneTransferResult(payload);
                    Debug.Log($"[Net] ZoneTransfer: result={data.Result}, zone={data.ZoneId}");
                    if (data.Result == ZoneTransferResult.SUCCESS)
                        CurrentZone = (int)data.ZoneId;
                    OnZoneTransferResult?.Invoke(data);
                    break;
                }

                case MsgType.SKILL_LIST_RESP:
                {
                    var skills = PacketBuilder.ParseSkillListResp(payload);
                    Debug.Log($"[Net] SkillList: {skills.Length} skills");
                    OnSkillList?.Invoke(skills);
                    break;
                }

                case MsgType.SKILL_RESULT:
                {
                    var data = PacketBuilder.ParseSkillResult(payload);
                    Debug.Log($"[Net] SkillResult: result={data.Result}, skill={data.SkillId}, dmg={data.Damage}");
                    OnSkillResult?.Invoke(data);
                    break;
                }

                case MsgType.PARTY_INFO:
                {
                    var data = PacketBuilder.ParsePartyInfo(payload);
                    Debug.Log($"[Net] PartyInfo: result={data.Result}, partyId={data.PartyId}, members={data.Members.Length}");
                    OnPartyInfo?.Invoke(data);
                    break;
                }

                case MsgType.INSTANCE_ENTER:
                {
                    var data = PacketBuilder.ParseInstanceEnter(payload);
                    Debug.Log($"[Net] InstanceEnter: result={data.Result}, instanceId={data.InstanceId}");
                    OnInstanceEnter?.Invoke(data);
                    break;
                }

                case MsgType.INSTANCE_LEAVE_RESULT:
                {
                    var data = PacketBuilder.ParseInstanceLeaveResult(payload);
                    Debug.Log($"[Net] InstanceLeave: result={data.Result}, zone={data.ZoneId}");
                    OnInstanceLeaveResult?.Invoke(data);
                    break;
                }

                case MsgType.INSTANCE_INFO:
                {
                    var data = PacketBuilder.ParseInstanceInfo(payload);
                    Debug.Log($"[Net] InstanceInfo: id={data.InstanceId}, players={data.PlayerCount}, monsters={data.MonsterCount}");
                    OnInstanceInfo?.Invoke(data);
                    break;
                }

                case MsgType.MATCH_FOUND:
                {
                    var data = PacketBuilder.ParseMatchFound(payload);
                    Debug.Log($"[Net] MatchFound: matchId={data.MatchId}, players={data.PlayerCount}");
                    OnMatchFound?.Invoke(data);
                    break;
                }

                case MsgType.MATCH_STATUS:
                {
                    var data = PacketBuilder.ParseMatchStatus(payload);
                    Debug.Log($"[Net] MatchStatus: status={data.Status}, pos={data.QueuePosition}");
                    OnMatchStatus?.Invoke(data);
                    break;
                }

                case MsgType.INVENTORY_RESP:
                {
                    var items = PacketBuilder.ParseInventoryResp(payload);
                    Debug.Log($"[Net] Inventory: {items.Length} items");
                    OnInventoryResp?.Invoke(items);
                    break;
                }

                case MsgType.ITEM_ADD_RESULT:
                {
                    var data = PacketBuilder.ParseItemAddResult(payload);
                    Debug.Log($"[Net] ItemAdd: result={data.Result}, slot={data.Slot}, item={data.ItemId}");
                    OnItemAddResult?.Invoke(data);
                    break;
                }

                case MsgType.ITEM_USE_RESULT:
                {
                    var data = PacketBuilder.ParseItemUseResult(payload);
                    Debug.Log($"[Net] ItemUse: result={data.Result}, slot={data.Slot}");
                    OnItemUseResult?.Invoke(data);
                    break;
                }

                case MsgType.ITEM_EQUIP_RESULT:
                {
                    var data = PacketBuilder.ParseItemEquipResult(payload);
                    Debug.Log($"[Net] ItemEquip: result={data.Result}, slot={data.Slot}, equipped={data.Equipped}");
                    OnItemEquipResult?.Invoke(data);
                    break;
                }

                case MsgType.BUFF_LIST_RESP:
                {
                    var buffs = PacketBuilder.ParseBuffListResp(payload);
                    Debug.Log($"[Net] BuffList: {buffs.Length} buffs");
                    OnBuffList?.Invoke(buffs);
                    break;
                }

                case MsgType.BUFF_RESULT:
                {
                    var data = PacketBuilder.ParseBuffResult(payload);
                    Debug.Log($"[Net] BuffResult: result={data.Result}, buffId={data.BuffId}");
                    OnBuffResult?.Invoke(data);
                    break;
                }

                case MsgType.BUFF_REMOVE_RESP:
                {
                    var data = PacketBuilder.ParseBuffRemoveResp(payload);
                    Debug.Log($"[Net] BuffRemove: result={data.Result}, buffId={data.BuffId}");
                    OnBuffRemoveResp?.Invoke(data);
                    break;
                }

                case MsgType.CONDITION_RESULT:
                {
                    byte result = payload[0];
                    Debug.Log($"[Net] ConditionResult: {result}");
                    OnConditionResult?.Invoke(result);
                    break;
                }

                case MsgType.SPATIAL_QUERY_RESP:
                {
                    var entries = PacketBuilder.ParseSpatialQueryResp(payload);
                    Debug.Log($"[Net] SpatialQuery: {entries.Length} results");
                    OnSpatialQueryResp?.Invoke(entries);
                    break;
                }

                case MsgType.LOOT_RESULT:
                {
                    var items = PacketBuilder.ParseLootResult(payload);
                    Debug.Log($"[Net] Loot: {items.Length} items");
                    OnLootResult?.Invoke(items);
                    break;
                }

                case MsgType.QUEST_LIST_RESP:
                {
                    var quests = PacketBuilder.ParseQuestListResp(payload);
                    Debug.Log($"[Net] QuestList: {quests.Length} quests");
                    OnQuestList?.Invoke(quests);
                    break;
                }

                case MsgType.QUEST_ACCEPT_RESULT:
                {
                    var data = PacketBuilder.ParseQuestAcceptResult(payload);
                    Debug.Log($"[Net] QuestAccept: result={data.Result}, questId={data.QuestId}");
                    OnQuestAcceptResult?.Invoke(data);
                    break;
                }

                case MsgType.QUEST_COMPLETE_RESULT:
                {
                    var data = PacketBuilder.ParseQuestCompleteResult(payload);
                    Debug.Log($"[Net] QuestComplete: result={data.Result}, questId={data.QuestId}, exp={data.RewardExp}");
                    OnQuestCompleteResult?.Invoke(data);
                    break;
                }

                // ━━━ 세션 35: 이동 검증 ━━━

                case MsgType.POSITION_CORRECTION:
                {
                    var (x, y, z) = PacketBuilder.ParsePositionCorrection(payload);
                    Debug.Log($"[Net] PositionCorrection: ({x},{y},{z})");
                    OnPositionCorrection?.Invoke(x, y, z);
                    break;
                }

                // ━━━ 세션 30: 채팅 ━━━

                case MsgType.CHAT_MESSAGE:
                {
                    var data = PacketBuilder.ParseChatMessage(payload);
                    Debug.Log($"[Net] ChatMessage: [{data.Channel}] {data.SenderName}: {data.Message}");
                    OnChatMessage?.Invoke(data);
                    break;
                }

                case MsgType.WHISPER_RESULT:
                {
                    var data = PacketBuilder.ParseWhisperResult(payload);
                    Debug.Log($"[Net] WhisperResult: {data.Result}, dir={data.Direction}, from={data.OtherName}");
                    OnWhisperResult?.Invoke(data);
                    break;
                }

                case MsgType.SYSTEM_MESSAGE:
                {
                    string msg = PacketBuilder.ParseSystemMessage(payload);
                    Debug.Log($"[Net] SystemMessage: {msg}");
                    OnSystemMessage?.Invoke(msg);
                    break;
                }

                // ━━━ 세션 32: 상점 ━━━

                case MsgType.SHOP_LIST:
                {
                    var data = PacketBuilder.ParseShopList(payload);
                    Debug.Log($"[Net] ShopList: npc={data.NpcId}, items={data.Items.Length}");
                    OnShopList?.Invoke(data);
                    break;
                }

                case MsgType.SHOP_RESULT:
                {
                    var data = PacketBuilder.ParseShopResult(payload);
                    Debug.Log($"[Net] ShopResult: {data.Result}, action={data.Action}, item={data.ItemId}, gold={data.Gold}");
                    OnShopResult?.Invoke(data);
                    break;
                }

                // ━━━ 세션 33: 스킬 확장 ━━━

                case MsgType.SKILL_LEVEL_UP_RESULT:
                {
                    var data = PacketBuilder.ParseSkillLevelUpResult(payload);
                    Debug.Log($"[Net] SkillLevelUp: {data.Result}, skill={data.SkillId}, lv={data.NewLevel}, points={data.SkillPoints}");
                    OnSkillLevelUpResult?.Invoke(data);
                    break;
                }

                case MsgType.SKILL_POINT_INFO:
                {
                    var data = PacketBuilder.ParseSkillPointInfo(payload);
                    Debug.Log($"[Net] SkillPointInfo: points={data.SkillPoints}, spent={data.TotalSpent}");
                    OnSkillPointInfo?.Invoke(data);
                    break;
                }

                // ━━━ 세션 34: 보스 ━━━

                case MsgType.BOSS_SPAWN:
                {
                    var data = PacketBuilder.ParseBossSpawn(payload);
                    Debug.Log($"[Net] BossSpawn: {data.Name} (id={data.BossId}), lv={data.Level}, hp={data.HP}/{data.MaxHP}, phase={data.Phase}");
                    OnBossSpawn?.Invoke(data);
                    break;
                }

                case MsgType.BOSS_PHASE_CHANGE:
                {
                    var data = PacketBuilder.ParseBossPhaseChange(payload);
                    Debug.Log($"[Net] BossPhaseChange: boss={data.BossId}, phase={data.NewPhase}, hp={data.HP}/{data.MaxHP}");
                    OnBossPhaseChange?.Invoke(data);
                    break;
                }

                case MsgType.BOSS_SPECIAL_ATTACK:
                {
                    var data = PacketBuilder.ParseBossSpecialAttack(payload);
                    Debug.Log($"[Net] BossSpecialAttack: boss={data.BossId}, type={data.AttackType}, dmg={data.Damage}");
                    OnBossSpecialAttack?.Invoke(data);
                    break;
                }

                case MsgType.BOSS_ENRAGE:
                {
                    var data = PacketBuilder.ParseBossEnrage(payload);
                    Debug.Log($"[Net] BossEnrage: boss={data.BossId}");
                    OnBossEnrage?.Invoke(data);
                    break;
                }

                case MsgType.BOSS_DEFEATED:
                {
                    var data = PacketBuilder.ParseBossDefeated(payload);
                    Debug.Log($"[Net] BossDefeated: boss={data.BossId}, killer={data.KillerEntityId}");
                    OnBossDefeated?.Invoke(data);
                    break;
                }

                // ━━━ 세션 36: 몬스터 AI ━━━

                case MsgType.MONSTER_MOVE:
                {
                    var data = PacketBuilder.ParseMonsterMove(payload);
                    OnMonsterMove?.Invoke(data);
                    break;
                }

                case MsgType.MONSTER_AGGRO:
                {
                    var data = PacketBuilder.ParseMonsterAggro(payload);
                    Debug.Log($"[Net] MonsterAggro: monster={data.MonsterEntityId}, target={data.TargetEntityId}");
                    OnMonsterAggro?.Invoke(data);
                    break;
                }

                // ━━━ 세션 37: 어드민 ━━━

                case MsgType.ADMIN_RELOAD_RESULT:
                {
                    var data = PacketBuilder.ParseAdminReloadResult(payload);
                    Debug.Log($"[Net] AdminReload: result={data.Result}, version={data.Version}, name={data.Name}");
                    OnAdminReloadResult?.Invoke(data);
                    break;
                }

                case MsgType.ADMIN_CONFIG_RESP:
                {
                    var data = PacketBuilder.ParseAdminConfigResp(payload);
                    Debug.Log($"[Net] AdminConfig: found={data.Found}, value={data.Value}");
                    OnAdminConfigResp?.Invoke(data);
                    break;
                }

                // ━━━ S033: 서버 선택 / 캐릭터 CRUD / 튜토리얼 ━━━

                case MsgType.SERVER_LIST:
                {
                    var servers = PacketBuilder.ParseServerList(payload);
                    Debug.Log($"[Net] ServerList: {servers.Length} servers");
                    OnServerList?.Invoke(servers);
                    break;
                }

                case MsgType.CHARACTER_LIST:
                {
                    var chars = PacketBuilder.ParseCharacterList(payload);
                    Debug.Log($"[Net] CharacterList: {chars.Length} characters");
                    OnCharacterDataList?.Invoke(chars);
                    break;
                }

                case MsgType.CHARACTER_CREATE_RESULT:
                {
                    var data = PacketBuilder.ParseCharacterCreateResult(payload);
                    Debug.Log($"[Net] CharacterCreate: result={data.Result}, charId={data.CharId}");
                    OnCharacterCreateResult?.Invoke(data);
                    break;
                }

                case MsgType.CHARACTER_DELETE_RESULT:
                {
                    var data = PacketBuilder.ParseCharacterDeleteResult(payload);
                    Debug.Log($"[Net] CharacterDelete: result={data.Result}, charId={data.CharId}");
                    OnCharacterDeleteResult?.Invoke(data);
                    break;
                }

                case MsgType.TUTORIAL_REWARD:
                {
                    var data = PacketBuilder.ParseTutorialReward(payload);
                    Debug.Log($"[Net] TutorialReward: step={data.StepId}, type={data.RewardType}, amount={data.Amount}");
                    OnTutorialReward?.Invoke(data);
                    break;
                }

                // ━━━ S034: NPC / 강화 ━━━

                case MsgType.NPC_DIALOG:
                {
                    var data = PacketBuilder.ParseNpcDialog(payload);
                    Debug.Log($"[Net] NpcDialog: npcId={data.NpcId}, type={data.Type}, lines={data.Lines.Length}, quests={data.QuestIds.Length}");
                    OnNpcDialog?.Invoke(data);
                    break;
                }

                case MsgType.ENHANCE_RESULT:
                {
                    var data = PacketBuilder.ParseEnhanceResult(payload);
                    Debug.Log($"[Net] EnhanceResult: slot={data.SlotIndex}, result={data.Result}, newLevel={data.NewLevel}");
                    OnEnhanceResult?.Invoke(data);
                    break;
                }

                // ━━━ S029: 문파 ━━━

                case MsgType.GUILD_INFO:
                {
                    var data = PacketBuilder.ParseGuildInfo(payload);
                    Debug.Log($"[Net] GuildInfo: id={data.GuildId}, name={data.Name}, members={data.Members.Length}");
                    OnGuildInfo?.Invoke(data);
                    break;
                }

                case MsgType.GUILD_LIST:
                {
                    var guilds = PacketBuilder.ParseGuildList(payload);
                    Debug.Log($"[Net] GuildList: {guilds.Length} guilds");
                    OnGuildList?.Invoke(guilds);
                    break;
                }

                // ━━━ S029: 거래 ━━━

                case MsgType.TRADE_RESULT:
                {
                    var data = PacketBuilder.ParseTradeResult(payload);
                    Debug.Log($"[Net] TradeResult: {data.Result}");
                    OnTradeResult?.Invoke(data);
                    break;
                }

                // ━━━ S029: 우편 ━━━

                case MsgType.MAIL_LIST:
                {
                    var mails = PacketBuilder.ParseMailList(payload);
                    Debug.Log($"[Net] MailList: {mails.Length} mails");
                    OnMailList?.Invoke(mails);
                    break;
                }

                case MsgType.MAIL_READ_RESP:
                {
                    var data = PacketBuilder.ParseMailReadResp(payload);
                    Debug.Log($"[Net] MailRead: id={data.MailId}, from={data.Sender}, gold={data.Gold}");
                    OnMailRead?.Invoke(data);
                    break;
                }

                case MsgType.MAIL_CLAIM_RESULT:
                {
                    var data = PacketBuilder.ParseMailClaimResult(payload);
                    Debug.Log($"[Net] MailClaim: result={data.Result}, id={data.MailId}");
                    OnMailClaimResult?.Invoke(data);
                    break;
                }

                case MsgType.MAIL_DELETE_RESULT:
                {
                    var data = PacketBuilder.ParseMailDeleteResult(payload);
                    Debug.Log($"[Net] MailDelete: result={data.Result}, id={data.MailId}");
                    OnMailDeleteResult?.Invoke(data);
                    break;
                }

                // ━━━ S036: PvP 아레나 ━━━

                case MsgType.PVP_QUEUE_STATUS:
                {
                    var data = PacketBuilder.ParsePvPQueueStatus(payload);
                    Debug.Log($"[Net] PvPQueueStatus: mode={data.ModeId}, status={data.Status}, count={data.QueueCount}");
                    OnPvPQueueStatus?.Invoke(data);
                    break;
                }

                case MsgType.PVP_MATCH_FOUND:
                {
                    var data = PacketBuilder.ParsePvPMatchFound(payload);
                    Debug.Log($"[Net] PvPMatchFound: matchId={data.MatchId}, mode={data.ModeId}, team={data.TeamId}");
                    OnPvPMatchFound?.Invoke(data);
                    break;
                }

                case MsgType.PVP_MATCH_START:
                {
                    var data = PacketBuilder.ParsePvPMatchStart(payload);
                    Debug.Log($"[Net] PvPMatchStart: matchId={data.MatchId}, team={data.TeamId}, timeLimit={data.TimeLimit}s");
                    OnPvPMatchStart?.Invoke(data);
                    break;
                }

                case MsgType.PVP_ATTACK_RESULT:
                {
                    var data = PacketBuilder.ParsePvPAttackResult(payload);
                    Debug.Log($"[Net] PvPAttackResult: matchId={data.MatchId}, dmg={data.Damage}, hp={data.RemainingHP}");
                    OnPvPAttackResult?.Invoke(data);
                    break;
                }

                case MsgType.PVP_MATCH_END:
                {
                    var data = PacketBuilder.ParsePvPMatchEnd(payload);
                    Debug.Log($"[Net] PvPMatchEnd: matchId={data.MatchId}, won={data.Won}, rating={data.NewRating}, tier={data.Tier}");
                    OnPvPMatchEnd?.Invoke(data);
                    break;
                }

                case MsgType.PVP_RATING_INFO:
                {
                    var data = PacketBuilder.ParsePvPRatingInfo(payload);
                    Debug.Log($"[Net] PvPRatingInfo: rating={data.Rating}, tier={data.Tier}, W={data.Wins}/L={data.Losses}");
                    OnPvPRatingInfo?.Invoke(data);
                    break;
                }

                // ━━━ S036: 레이드 보스 ━━━

                case MsgType.RAID_BOSS_SPAWN:
                {
                    var data = PacketBuilder.ParseRaidBossSpawn(payload);
                    Debug.Log($"[Net] RaidBossSpawn: {data.BossName}, hp={data.CurrentHP}/{data.MaxHP}, phase={data.Phase}/{data.MaxPhases}, enrage={data.EnrageTimer}s");
                    OnRaidBossSpawn?.Invoke(data);
                    break;
                }

                case MsgType.RAID_PHASE_CHANGE:
                {
                    var data = PacketBuilder.ParseRaidPhaseChange(payload);
                    Debug.Log($"[Net] RaidPhaseChange: phase={data.Phase}/{data.MaxPhases}");
                    OnRaidPhaseChange?.Invoke(data);
                    break;
                }

                case MsgType.RAID_MECHANIC:
                {
                    var data = PacketBuilder.ParseRaidMechanic(payload);
                    Debug.Log($"[Net] RaidMechanic: id={data.MechanicId}, phase={data.Phase}");
                    OnRaidMechanic?.Invoke(data);
                    break;
                }

                case MsgType.RAID_MECHANIC_RESULT:
                {
                    var data = PacketBuilder.ParseRaidMechanicResult(payload);
                    Debug.Log($"[Net] RaidMechanicResult: id={data.MechanicId}, success={data.Success}");
                    OnRaidMechanicResult?.Invoke(data);
                    break;
                }

                case MsgType.RAID_STAGGER:
                {
                    var data = PacketBuilder.ParseRaidStagger(payload);
                    Debug.Log($"[Net] RaidStagger: gauge={data.StaggerGauge}");
                    OnRaidStagger?.Invoke(data);
                    break;
                }

                case MsgType.RAID_ENRAGE:
                {
                    uint instanceId = BitConverter.ToUInt32(payload, 0);
                    Debug.Log($"[Net] RaidEnrage: instance={instanceId}");
                    OnRaidEnrage?.Invoke(instanceId);
                    break;
                }

                case MsgType.RAID_WIPE:
                {
                    var data = PacketBuilder.ParseRaidWipe(payload);
                    Debug.Log($"[Net] RaidWipe: instance={data.InstanceId}, phase={data.Phase}");
                    OnRaidWipe?.Invoke(data);
                    break;
                }

                case MsgType.RAID_CLEAR:
                {
                    var data = PacketBuilder.ParseRaidClear(payload);
                    Debug.Log($"[Net] RaidClear: gold={data.Gold}, exp={data.Exp}, tokens={data.Tokens}");
                    OnRaidClear?.Invoke(data);
                    break;
                }

                case MsgType.RAID_ATTACK_RESULT:
                {
                    var data = PacketBuilder.ParseRaidAttackResult(payload);
                    Debug.Log($"[Net] RaidAttackResult: dmg={data.Damage}, hp={data.CurrentHP}/{data.MaxHP}");
                    OnRaidAttackResult?.Invoke(data);
                    break;
                }

                // ━━━ S045: 거래소 ━━━

                case MsgType.AUCTION_LIST:
                {
                    var data = PacketBuilder.ParseAuctionList(payload);
                    Debug.Log($"[Net] AuctionList: total={data.TotalCount}, page={data.CurrentPage}/{data.TotalPages}, items={data.Items.Length}");
                    OnAuctionList?.Invoke(data);
                    break;
                }

                case MsgType.AUCTION_REGISTER_RESULT:
                {
                    var data = PacketBuilder.ParseAuctionRegisterResult(payload);
                    Debug.Log($"[Net] AuctionRegister: result={data.Result}, auctionId={data.AuctionId}");
                    OnAuctionRegisterResult?.Invoke(data);
                    break;
                }

                case MsgType.AUCTION_BUY_RESULT:
                {
                    var data = PacketBuilder.ParseAuctionBuyResult(payload);
                    Debug.Log($"[Net] AuctionBuy: result={data.Result}, auctionId={data.AuctionId}");
                    OnAuctionBuyResult?.Invoke(data);
                    break;
                }

                case MsgType.AUCTION_BID_RESULT:
                {
                    var data = PacketBuilder.ParseAuctionBidResult(payload);
                    Debug.Log($"[Net] AuctionBid: result={data.Result}, auctionId={data.AuctionId}");
                    OnAuctionBidResult?.Invoke(data);
                    break;
                }

                // ━━━ S041: 제작/채집/요리/인챈트/보석 ━━━

                case MsgType.CRAFT_LIST:
                {
                    var recipes = PacketBuilder.ParseCraftList(payload);
                    Debug.Log($"[Net] CraftList: {recipes.Length} recipes");
                    OnCraftList?.Invoke(recipes);
                    break;
                }

                case MsgType.CRAFT_RESULT:
                {
                    var data = PacketBuilder.ParseCraftResult(payload);
                    Debug.Log($"[Net] CraftResult: status={data.Status}, item={data.ItemId}, count={data.Count}, bonus={data.HasBonus}");
                    OnCraftResult?.Invoke(data);
                    break;
                }

                case MsgType.GATHER_RESULT:
                {
                    var data = PacketBuilder.ParseGatherResult(payload);
                    Debug.Log($"[Net] GatherResult: status={data.Status}, drops={data.Drops.Length}, energy={data.Energy}");
                    OnGatherResult?.Invoke(data);
                    break;
                }

                case MsgType.COOK_RESULT:
                {
                    var data = PacketBuilder.ParseCookResult(payload);
                    Debug.Log($"[Net] CookResult: status={data.Status}, duration={data.Duration}s, effects={data.EffectCount}");
                    OnCookResult?.Invoke(data);
                    break;
                }

                case MsgType.ENCHANT_RESULT:
                {
                    var data = PacketBuilder.ParseEnchantResultData(payload);
                    Debug.Log($"[Net] EnchantResult: status={data.Status}, element={data.Element}, lv={data.Level}, dmg%={data.DamagePct}");
                    OnEnchantResultResp?.Invoke(data);
                    break;
                }

                case MsgType.GEM_EQUIP_RESULT:
                {
                    var data = PacketBuilder.ParseGemEquipResult(payload);
                    Debug.Log($"[Net] GemEquipResult: status={data.Status}, slot={data.ItemSlot}/{data.GemSlot}, type={data.GemType}, tier={data.GemTier}");
                    OnGemEquipResult?.Invoke(data);
                    break;
                }

                case MsgType.GEM_FUSE_RESULT:
                {
                    var data = PacketBuilder.ParseGemFuseResult(payload);
                    Debug.Log($"[Net] GemFuseResult: status={data.Status}, type={data.GemType}, newTier={data.NewTier}");
                    OnGemFuseResult?.Invoke(data);
                    break;
                }

                // ━━━ S042: 캐시샵/배틀패스/이벤트 ━━━

                case MsgType.CASH_SHOP_LIST:
                {
                    var items = PacketBuilder.ParseCashShopList(payload);
                    Debug.Log($"[Net] CashShopList: {items.Length} items");
                    OnCashShopList?.Invoke(items);
                    break;
                }

                case MsgType.CASH_SHOP_BUY_RESULT:
                {
                    var data = PacketBuilder.ParseCashShopBuyResult(payload);
                    Debug.Log($"[Net] CashShopBuy: result={data.Result}, item={data.ItemId}, crystals={data.RemainingCrystals}");
                    OnCashShopBuyResult?.Invoke(data);
                    break;
                }

                case MsgType.BATTLEPASS_INFO:
                {
                    var data = PacketBuilder.ParseBattlePassInfo(payload);
                    Debug.Log($"[Net] BattlePassInfo: season={data.SeasonId}, lv={data.Level}, exp={data.Exp}/{data.MaxExp}, premium={data.IsPremium}");
                    OnBattlePassInfo?.Invoke(data);
                    break;
                }

                case MsgType.BATTLEPASS_REWARD_RESULT:
                {
                    var data = PacketBuilder.ParseBattlePassRewardResult(payload);
                    Debug.Log($"[Net] BattlePassReward: result={data.Result}, lv={data.Level}, track={data.Track}");
                    OnBattlePassRewardResult?.Invoke(data);
                    break;
                }

                case MsgType.BATTLEPASS_BUY_RESULT:
                {
                    var data = PacketBuilder.ParseBattlePassBuyResult(payload);
                    Debug.Log($"[Net] BattlePassBuy: result={data.Result}, crystals={data.RemainingCrystals}");
                    OnBattlePassBuyResult?.Invoke(data);
                    break;
                }

                case MsgType.EVENT_LIST:
                {
                    var events = PacketBuilder.ParseEventList(payload);
                    Debug.Log($"[Net] EventList: {events.Length} events");
                    OnEventList?.Invoke(events);
                    break;
                }

                case MsgType.EVENT_CLAIM_RESULT:
                {
                    var data = PacketBuilder.ParseEventClaimResult(payload);
                    Debug.Log($"[Net] EventClaim: result={data.Result}, event={data.EventId}");
                    OnEventClaimResult?.Invoke(data);
                    break;
                }

                case MsgType.SUBSCRIPTION_INFO:
                {
                    var data = PacketBuilder.ParseSubscriptionInfo(payload);
                    Debug.Log($"[Net] Subscription: active={data.IsActive}, days={data.DaysLeft}, daily={data.DailyCrystals}");
                    OnSubscriptionInfo?.Invoke(data);
                    break;
                }

                // ━━━ S042: 월드 시스템 ━━━

                case MsgType.WEATHER_UPDATE:
                {
                    var data = PacketBuilder.ParseWeatherUpdate(payload);
                    Debug.Log($"[Net] WeatherUpdate: zone={data.ZoneId}, weather={data.Weather}, transition={data.TransitionSeconds}s");
                    OnWeatherUpdate?.Invoke(data);
                    break;
                }

                case MsgType.TIME_UPDATE:
                {
                    uint gameTime = BitConverter.ToUInt32(payload, 0);
                    OnTimeUpdate?.Invoke(gameTime);
                    break;
                }

                case MsgType.TELEPORT_LIST:
                {
                    var waypoints = PacketBuilder.ParseTeleportList(payload);
                    Debug.Log($"[Net] TeleportList: {waypoints.Length} waypoints");
                    OnTeleportList?.Invoke(waypoints);
                    break;
                }

                case MsgType.TELEPORT_RESULT:
                {
                    var data = PacketBuilder.ParseTeleportResult(payload);
                    Debug.Log($"[Net] TeleportResult: result={data.Result}, zone={data.ZoneId}");
                    if (data.Result == TeleportResult.SUCCESS)
                        CurrentZone = (int)data.ZoneId;
                    OnTeleportResult?.Invoke(data);
                    break;
                }

                case MsgType.WORLD_OBJECT_RESULT:
                {
                    var data = PacketBuilder.ParseWorldObjectResult(payload);
                    Debug.Log($"[Net] WorldObjectResult: result={data.Result}, obj={data.ObjectId}, item={data.ItemId}, gold={data.Gold}");
                    OnWorldObjectResult?.Invoke(data);
                    break;
                }

                case MsgType.MOUNT_RESULT:
                {
                    var data = PacketBuilder.ParseMountResult(payload);
                    Debug.Log($"[Net] MountResult: result={data.Result}, mount={data.MountId}, speed={data.SpeedMultiplied / 100f}x");
                    OnMountResult?.Invoke(data);
                    break;
                }

                case MsgType.MOUNT_DISMOUNT_RESULT:
                {
                    byte result = payload[0];
                    Debug.Log($"[Net] MountDismount: result={result}");
                    OnMountDismountResult?.Invoke(result);
                    break;
                }

                // ━━━ S042: 출석/리셋/컨텐츠 해금 ━━━

                case MsgType.ATTENDANCE_INFO:
                {
                    var data = PacketBuilder.ParseAttendanceInfo(payload);
                    Debug.Log($"[Net] AttendanceInfo: day={data.CurrentDay}, total={data.TotalDays}");
                    OnAttendanceInfo?.Invoke(data);
                    break;
                }

                case MsgType.ATTENDANCE_CLAIM_RESULT:
                {
                    var data = PacketBuilder.ParseAttendanceClaimResult(payload);
                    Debug.Log($"[Net] AttendanceClaim: result={data.Result}, day={data.Day}");
                    OnAttendanceClaimResult?.Invoke(data);
                    break;
                }

                case MsgType.DAILY_RESET_NOTIFY:
                {
                    var data = PacketBuilder.ParseDailyResetNotify(payload);
                    Debug.Log($"[Net] DailyReset: type={data.Type}");
                    OnDailyResetNotify?.Invoke(data);
                    break;
                }

                case MsgType.CONTENT_UNLOCK_NOTIFY:
                {
                    var data = PacketBuilder.ParseContentUnlockNotify(payload);
                    Debug.Log($"[Net] ContentUnlock: type={data.UnlockType}, system={data.SystemName}");
                    OnContentUnlockNotify?.Invoke(data);
                    break;
                }

                case MsgType.LOGIN_REWARD_NOTIFY:
                {
                    var data = PacketBuilder.ParseLoginRewardNotify(payload);
                    Debug.Log($"[Net] LoginReward: type={data.RewardType}, id={data.RewardId}, count={data.RewardCount}");
                    OnLoginRewardNotify?.Invoke(data);
                    break;
                }

                // ━━━ S042: 스토리/대화 시스템 ━━━

                case MsgType.DIALOG_CHOICE_RESULT:
                {
                    var data = PacketBuilder.ParseDialogChoiceResult(payload);
                    Debug.Log($"[Net] DialogChoice: npc={data.NpcId}, lines={data.Lines.Length}, choices={data.Choices.Length}");
                    OnDialogChoiceResult?.Invoke(data);
                    break;
                }

                case MsgType.CUTSCENE_TRIGGER:
                {
                    var data = PacketBuilder.ParseCutsceneTrigger(payload);
                    Debug.Log($"[Net] CutsceneTrigger: id={data.CutsceneId}, duration={data.DurationSeconds}s");
                    OnCutsceneTrigger?.Invoke(data);
                    break;
                }

                case MsgType.CUTSCENE_END:
                {
                    ushort cutsceneId = BitConverter.ToUInt16(payload, 0);
                    Debug.Log($"[Net] CutsceneEnd: id={cutsceneId}");
                    OnCutsceneEnd?.Invoke(cutsceneId);
                    break;
                }

                case MsgType.STORY_PROGRESS:
                {
                    var data = PacketBuilder.ParseStoryProgress(payload);
                    Debug.Log($"[Net] StoryProgress: chapter={data.Chapter}, quest={data.QuestId}, state={data.QuestState}");
                    OnStoryProgress?.Invoke(data);
                    break;
                }

                case MsgType.MAIN_QUEST_DATA:
                {
                    var data = PacketBuilder.ParseMainQuestData(payload);
                    Debug.Log($"[Net] MainQuestData: id={data.QuestId}, name={data.Name}, objectives={data.Objectives.Length}");
                    OnMainQuestData?.Invoke(data);
                    break;
                }

                // ━━━ S046: 비급 & 트라이포드 ━━━

                case MsgType.TRIPOD_LIST:
                {
                    var data = PacketBuilder.ParseTripodList(payload);
                    Debug.Log($"[Net] TripodList: skills={data.Skills.Length}");
                    OnTripodList?.Invoke(data);
                    break;
                }

                case MsgType.TRIPOD_EQUIP_RESULT:
                {
                    var data = PacketBuilder.ParseTripodEquipResult(payload);
                    Debug.Log($"[Net] TripodEquip: result={data}");
                    OnTripodEquipResult?.Invoke(data);
                    break;
                }

                case MsgType.SCROLL_DISCOVER:
                {
                    var data = PacketBuilder.ParseScrollDiscoverResult(payload);
                    Debug.Log($"[Net] ScrollDiscover: result={data.Result}, skill={data.SkillId}, tier={data.Tier}, opt={data.OptionIdx}");
                    OnScrollDiscoverResult?.Invoke(data);
                    break;
                }

                // ━━━ S047: 현상금 시스템 ━━━

                case MsgType.BOUNTY_LIST:
                {
                    var data = PacketBuilder.ParseBountyList(payload);
                    Debug.Log($"[Net] BountyList: daily={data.DailyBounties.Length}, weekly={data.HasWeekly}, accepted={data.AcceptedCount}");
                    OnBountyList?.Invoke(data);
                    break;
                }

                case MsgType.BOUNTY_ACCEPT_RESULT:
                {
                    var data = PacketBuilder.ParseBountyAcceptResult(payload);
                    Debug.Log($"[Net] BountyAccept: result={data.Result}, bountyId={data.BountyId}");
                    OnBountyAcceptResult?.Invoke(data);
                    break;
                }

                case MsgType.BOUNTY_COMPLETE:
                {
                    var data = PacketBuilder.ParseBountyComplete(payload);
                    Debug.Log($"[Net] BountyComplete: result={data.Result}, bountyId={data.BountyId}, gold={data.Gold}, exp={data.Exp}, token={data.Token}");
                    OnBountyComplete?.Invoke(data);
                    break;
                }

                case MsgType.BOUNTY_RANKING:
                {
                    var data = PacketBuilder.ParseBountyRanking(payload);
                    Debug.Log($"[Net] BountyRanking: count={data.Rankings.Length}, myRank={data.MyRank}, myScore={data.MyScore}");
                    OnBountyRanking?.Invoke(data);
                    break;
                }

                case MsgType.PVP_BOUNTY_NOTIFY:
                {
                    var data = PacketBuilder.ParsePvPBountyNotify(payload);
                    Debug.Log($"[Net] PvPBounty: target={data.TargetEntity}, tier={data.Tier}, streak={data.KillStreak}, gold={data.GoldReward}, name={data.Name}");
                    OnPvPBountyNotify?.Invoke(data);
                    break;
                }

                // ━━━ S048: 퀘스트 심화 (TASK 4) ━━━
                case MsgType.DAILY_QUEST_LIST:
                {
                    var data = PacketBuilder.ParseDailyQuestList(payload);
                    Debug.Log($"[Net] DailyQuestList: count={data.Quests.Length}");
                    OnDailyQuestList?.Invoke(data);
                    break;
                }
                case MsgType.WEEKLY_QUEST:
                {
                    var data = PacketBuilder.ParseWeeklyQuest(payload);
                    Debug.Log($"[Net] WeeklyQuest: hasQuest={data.HasQuest}");
                    OnWeeklyQuest?.Invoke(data);
                    break;
                }
                case MsgType.REPUTATION_INFO:
                {
                    var data = PacketBuilder.ParseReputationInfo(payload);
                    Debug.Log($"[Net] ReputationInfo: factions={data.Factions.Length}");
                    OnReputationInfo?.Invoke(data);
                    break;
                }

                // ━━━ S049: 칭호/도감/2차전직 (TASK 7) ━━━

                case MsgType.TITLE_LIST:
                {
                    var data = PacketBuilder.ParseTitleList(payload);
                    Debug.Log($"[Net] TitleList: equipped={data.EquippedId}, count={data.Titles.Length}");
                    OnTitleList?.Invoke(data);
                    break;
                }
                case MsgType.TITLE_EQUIP_RESULT:
                {
                    var data = PacketBuilder.ParseTitleEquipResult(payload);
                    Debug.Log($"[Net] TitleEquip: result={data.Result}, titleId={data.TitleId}");
                    OnTitleEquipResult?.Invoke(data);
                    break;
                }
                case MsgType.COLLECTION_INFO:
                {
                    var data = PacketBuilder.ParseCollectionInfo(payload);
                    Debug.Log($"[Net] CollectionInfo: monsters={data.MonsterCategories.Length}, equips={data.EquipTiers.Length}");
                    OnCollectionInfo?.Invoke(data);
                    break;
                }
                case MsgType.JOB_CHANGE_RESULT:
                {
                    var data = PacketBuilder.ParseJobChangeResult(payload);
                    Debug.Log($"[Net] JobChange: result={data.Result}, job={data.JobName}, bonuses={data.Bonuses.Length}, skills={data.NewSkills.Length}");
                    OnJobChangeResult?.Invoke(data);
                    break;
                }

                // ━━━ S050: 각인/초월 (TASK 8 Enhancement) ━━━

                case MsgType.ENGRAVING_LIST:
                {
                    var data = PacketBuilder.ParseEngravingList(payload);
                    Debug.Log($"[Net] EngravingList: count={data.Engravings.Length}");
                    OnEngravingList?.Invoke(data);
                    break;
                }
                case MsgType.ENGRAVING_RESULT:
                {
                    var data = PacketBuilder.ParseEngravingResult(payload);
                    Debug.Log($"[Net] EngravingResult: result={data.Result}, name={data.Name}, activeCount={data.ActiveCount}");
                    OnEngravingResult?.Invoke(data);
                    break;
                }
                case MsgType.TRANSCEND_RESULT:
                {
                    var data = PacketBuilder.ParseTranscendResult(payload);
                    Debug.Log($"[Net] TranscendResult: result={data.Result}, slot={data.Slot}, level={data.NewLevel}, cost={data.GoldCost}, success={data.Success}");
                    OnTranscendResult?.Invoke(data);
                    break;
                }

                // ━━━ S051: 소셜 심화 (TASK 5) ━━━

                case MsgType.FRIEND_REQUEST_RESULT:
                {
                    var result = PacketBuilder.ParseFriendRequestResult(payload);
                    Debug.Log($"[Net] FriendRequestResult: {result}");
                    OnFriendRequestResult?.Invoke(result);
                    break;
                }
                case MsgType.FRIEND_LIST:
                {
                    var data = PacketBuilder.ParseFriendList(payload);
                    Debug.Log($"[Net] FriendList: count={data.Friends.Length}");
                    OnFriendList?.Invoke(data);
                    break;
                }
                case MsgType.BLOCK_RESULT:
                {
                    var result = PacketBuilder.ParseBlockResult(payload);
                    Debug.Log($"[Net] BlockResult: {result}");
                    OnBlockResult?.Invoke(result);
                    break;
                }
                case MsgType.BLOCK_LIST:
                {
                    var data = PacketBuilder.ParseBlockList(payload);
                    Debug.Log($"[Net] BlockList: count={data.Names.Length}");
                    OnBlockList?.Invoke(data);
                    break;
                }
                case MsgType.PARTY_FINDER_LIST:
                {
                    var data = PacketBuilder.ParsePartyFinderList(payload);
                    Debug.Log($"[Net] PartyFinderList: count={data.Listings.Length}");
                    OnPartyFinderList?.Invoke(data);
                    break;
                }

                // ━━━ S052: 내구도/수리/리롤 (TASK 9) ━━━

                case MsgType.REPAIR_RESULT:
                {
                    var data = PacketBuilder.ParseRepairResult(payload);
                    Debug.Log($"[Net] RepairResult: result={data.Result}, cost={data.TotalCost}, count={data.RepairedCount}");
                    OnRepairResult?.Invoke(data);
                    break;
                }
                case MsgType.REROLL_RESULT:
                {
                    var data = PacketBuilder.ParseRerollResult(payload);
                    Debug.Log($"[Net] RerollResult: result={data.Result}, opts={data.Options.Length}");
                    OnRerollResult?.Invoke(data);
                    break;
                }
                case MsgType.DURABILITY_NOTIFY:
                {
                    var data = PacketBuilder.ParseDurabilityNotify(payload);
                    Debug.Log($"[Net] DurabilityNotify: slot={data.InvSlot}, dur={data.Durability:F1}, broken={data.IsBroken}");
                    OnDurabilityNotify?.Invoke(data);
                    break;
                }

                // ━━━ S053: 전장/길드전/PvP시즌 (TASK 6) ━━━

                case MsgType.BATTLEGROUND_STATUS:
                {
                    var data = PacketBuilder.ParseBattlegroundStatus(payload);
                    Debug.Log($"[Net] BattlegroundStatus: status={data.Status}, match={data.MatchId}, mode={data.Mode}, team={data.Team}");
                    OnBattlegroundStatus?.Invoke(data);
                    break;
                }
                case MsgType.BATTLEGROUND_SCORE_UPDATE:
                {
                    var data = PacketBuilder.ParseBattlegroundScoreUpdate(payload);
                    Debug.Log($"[Net] BattlegroundScore: mode={data.Mode}, red={data.RedScore}, blue={data.BlueScore}, time={data.TimeRemaining}");
                    OnBattlegroundScoreUpdate?.Invoke(data);
                    break;
                }
                case MsgType.GUILD_WAR_STATUS:
                {
                    var data = PacketBuilder.ParseGuildWarStatus(payload);
                    Debug.Log($"[Net] GuildWarStatus: status={data.Status}, war={data.WarId}, hpA={data.CrystalHpA}, hpB={data.CrystalHpB}");
                    OnGuildWarStatus?.Invoke(data);
                    break;
                }

                // ━━━ S054: 보조 화폐/토큰 상점 (TASK 10) ━━━

                case MsgType.CURRENCY_INFO:
                {
                    var data = PacketBuilder.ParseCurrencyInfo(payload);
                    Debug.Log($"[Net] CurrencyInfo: gold={data.Gold}, silver={data.Silver}, dt={data.DungeonToken}, pvp={data.PvpToken}, gc={data.GuildContribution}");
                    OnCurrencyInfo?.Invoke(data);
                    break;
                }
                case MsgType.TOKEN_SHOP:
                {
                    var data = PacketBuilder.ParseTokenShop(payload);
                    Debug.Log($"[Net] TokenShop: type={data.ShopType}, items={data.Items.Length}");
                    OnTokenShop?.Invoke(data);
                    break;
                }
                case MsgType.TOKEN_SHOP_BUY_RESULT:
                {
                    var data = PacketBuilder.ParseTokenShopBuyResult(payload);
                    Debug.Log($"[Net] TokenShopBuyResult: result={data.Result}, shopId={data.ShopId}, remaining={data.RemainingCurrency}");
                    OnTokenShopBuyResult?.Invoke(data);
                    break;
                }

                default:
                    Debug.Log($"[Net] Unknown packet: type={type}, len={payload.Length}");
                    break;
            }
        }
    }
}
