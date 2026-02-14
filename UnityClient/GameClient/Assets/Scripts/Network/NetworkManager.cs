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

                default:
                    Debug.Log($"[Net] Unknown packet: type={type}, len={payload.Length}");
                    break;
            }
        }
    }
}
