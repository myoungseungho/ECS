// ━━━ ConnectionTest.cs ━━━
// Phase 2 TCP 브릿지 연동 테스트 (S035 전체 테스트 매트릭스)
// Gate 경유 / DirectConnect 모드 지원
// 키보드: Space=이동, T=채팅, N=NPC, E=강화, U=튜토리얼, S=서버목록, C=캐릭터목록

using UnityEngine;
using Network;

public class ConnectionTest : MonoBehaviour
{
    public enum ConnectionMode { Gate, DirectConnect }

    [Header("Connection")]
    [SerializeField] private ConnectionMode mode = ConnectionMode.DirectConnect;
    [SerializeField] private string directHost = "127.0.0.1";
    [SerializeField] private int directPort = 7777;

    [Header("Auto Test")]
    [SerializeField] private bool autoFullTest = true;
    [SerializeField] private float testStartDelay = 1.5f;

    private bool _testStarted;
    private int _passCount;
    private int _failCount;

    void Start()
    {
        var net = NetworkManager.Instance;

        // ━━━ 기존 이벤트 ━━━
        net.OnLoginResult += (result, accountId) => {
            LogResult("LOGIN_RESULT", result == LoginResult.Success,
                $"result={result}, accountId={accountId}");
            if (result == LoginResult.Success)
                net.SelectCharacter(1);
        };

        net.OnEnterGame += (r) => {
            LogResult("ENTER_GAME", r.ResultCode == 0,
                $"entity={r.EntityId}, zone={r.ZoneId}, pos=({r.X},{r.Y},{r.Z})");
            if (r.ResultCode == 0)
                net.JoinChannel(1);
        };

        net.OnEntityAppear += (eid, x, y, z) =>
            Debug.Log($"[Test] APPEAR: entity={eid} at ({x},{y},{z})");

        net.OnEntityMove += (eid, x, y, z) =>
            Debug.Log($"[Test] MOVE_BROADCAST: entity={eid} -> ({x},{y},{z})");

        net.OnEntityDisappear += (eid) =>
            Debug.Log($"[Test] DISAPPEAR: entity={eid}");

        // ━━━ Phase 2 기본 이벤트 ━━━
        net.OnMonsterSpawn += (data) =>
            LogResult("MONSTER_SPAWN", true,
                $"entity={data.EntityId}, monsterId={data.MonsterId}, lv={data.Level}, hp={data.HP}/{data.MaxHP}");

        net.OnMonsterMove += (data) =>
            Debug.Log($"[Test] MONSTER_MOVE: entity={data.EntityId} -> ({data.X},{data.Y},{data.Z})");

        net.OnMonsterAggro += (data) =>
            Debug.Log($"[Test] MONSTER_AGGRO: monster={data.MonsterEntityId}, target={data.TargetEntityId}");

        net.OnStatSync += (data) =>
            LogResult("STAT_SYNC", data.MaxHP > 0,
                $"hp={data.HP}/{data.MaxHP}, mp={data.MP}/{data.MaxMP}, lv={data.Level}, atk={data.ATK}, def={data.DEF}");

        net.OnSkillList += (skills) =>
            LogResult("SKILL_LIST", true, $"{skills.Length} skills");

        net.OnInventoryResp += (items) =>
            LogResult("INVENTORY", true, $"{items.Length} items");

        net.OnBuffList += (buffs) =>
            LogResult("BUFF_LIST", true, $"{buffs.Length} buffs");

        net.OnQuestList += (quests) =>
            LogResult("QUEST_LIST", true, $"{quests.Length} quests");

        net.OnChatMessage += (data) =>
            LogResult("CHAT_MESSAGE", true,
                $"ch={data.Channel}, sender={data.SenderName}, msg={data.Message}");

        net.OnSystemMessage += (msg) =>
            Debug.Log($"[Test] SYSTEM_MSG: {msg}");

        net.OnAttackResult += (data) =>
            LogResult("ATTACK_RESULT", true,
                $"result={data.Result}, dmg={data.Damage}, targetHP={data.TargetHP}/{data.TargetMaxHP}");

        // ━━━ S033: 서버 선택 / 캐릭터 CRUD / 튜토리얼 ━━━
        net.OnServerList += (servers) =>
            LogResult("SERVER_LIST", servers.Length > 0,
                $"{servers.Length} servers" + (servers.Length > 0 ? $" (first: {servers[0].Name}, status={servers[0].Status})" : ""));

        net.OnCharacterDataList += (chars) =>
            LogResult("CHARACTER_LIST", true, $"{chars.Length} characters");

        net.OnCharacterCreateResult += (data) =>
            LogResult("CHARACTER_CREATE", data.Result == CharacterCreateResult.SUCCESS || data.Result == CharacterCreateResult.NAME_EXISTS,
                $"result={data.Result}, charId={data.CharId}");

        net.OnCharacterDeleteResult += (data) =>
            LogResult("CHARACTER_DELETE", true, $"result={data.Result}, charId={data.CharId}");

        net.OnTutorialReward += (data) =>
            LogResult("TUTORIAL_REWARD", true,
                $"step={data.StepId}, type={data.RewardType}, amount={data.Amount}");

        // ━━━ S034: NPC / 강화 ━━━
        net.OnNpcDialog += (data) =>
            LogResult("NPC_DIALOG", true,
                $"npcId={data.NpcId}, type={data.Type}, lines={data.Lines.Length}, quests={data.QuestIds.Length}");

        net.OnEnhanceResult += (data) =>
            LogResult("ENHANCE_RESULT", true,
                $"slot={data.SlotIndex}, result={data.Result}, newLevel={data.NewLevel}");

        // ━━━ 에러 / 연결 끊김 ━━━
        net.OnError += (msg) =>
            Debug.LogError($"[Test] NET ERROR: {msg}");

        net.OnDisconnected += () =>
            Debug.LogWarning("[Test] DISCONNECTED");

        // ━━━ 접속 시작 ━━━
        if (mode == ConnectionMode.DirectConnect)
        {
            Debug.Log($"[Test] DirectConnect to {directHost}:{directPort}");
            net.ConnectDirect(directHost, directPort);
            Invoke(nameof(DoLogin), 0.5f);
        }
        else
        {
            Debug.Log("[Test] Connecting to Gate...");
            net.ConnectToGate();
            Invoke(nameof(DoLogin), 1.0f);
        }
    }

    void DoLogin()
    {
        Debug.Log("[Test] Logging in...");
        NetworkManager.Instance.Login("hero", "pass123");
    }

    void Update()
    {
        if (NetworkManager.Instance == null ||
            NetworkManager.Instance.State != NetworkManager.ConnectionState.InGame)
            return;

        // 자동 전체 테스트 (입장 후 testStartDelay초)
        if (autoFullTest && !_testStarted)
        {
            _testStarted = true;
            Invoke(nameof(RunFullTestSequence), testStartDelay);
        }

        // ━━━ 수동 키 테스트 ━━━

        // Space: 랜덤 이동
        if (Input.GetKeyDown(KeyCode.Space))
        {
            float x = Random.Range(50f, 950f);
            float y = Random.Range(50f, 950f);
            NetworkManager.Instance.SendMove(x, y, 0);
            Debug.Log($"[Test] Sent MOVE: ({x},{y})");
        }

        // T: 채팅
        if (Input.GetKeyDown(KeyCode.T))
            NetworkManager.Instance.SendChat(ChatChannel.GENERAL, "Manual chat test!");

        // N: NPC 인터랙션
        if (Input.GetKeyDown(KeyCode.N))
            NetworkManager.Instance.InteractNpc(1);

        // E: 강화
        if (Input.GetKeyDown(KeyCode.E))
            NetworkManager.Instance.RequestEnhance(0);

        // U: 튜토리얼
        if (Input.GetKeyDown(KeyCode.U))
            NetworkManager.Instance.CompleteTutorialStep(1);

        // S: 서버 목록
        if (Input.GetKeyDown(KeyCode.S))
            NetworkManager.Instance.RequestServerList();

        // C: 캐릭터 목록
        if (Input.GetKeyDown(KeyCode.C))
            NetworkManager.Instance.RequestCharacterList();
    }

    /// <summary>S035 11-step 자동 테스트 시퀀스</summary>
    void RunFullTestSequence()
    {
        Debug.Log("[Test] ═══ Phase 2 Full Test Sequence Start ═══");
        var net = NetworkManager.Instance;

        // 7. MOVE
        net.SendMove(500f, 500f, 0f);
        Debug.Log("[Test] Sent MOVE (500, 500)");

        // 8. CHAT
        Invoke(nameof(TestChat), 0.5f);
        // 9. NPC
        Invoke(nameof(TestNpc), 1.0f);
        // 10. ENHANCE
        Invoke(nameof(TestEnhance), 1.5f);
        // 11. TUTORIAL
        Invoke(nameof(TestTutorial), 2.0f);
        // Summary
        Invoke(nameof(PrintSummary), 4.0f);
    }

    void TestChat()
    {
        Debug.Log("[Test] Sending CHAT...");
        NetworkManager.Instance.SendChat(ChatChannel.GENERAL, "Hello from Phase2 Unity!");
    }

    void TestNpc()
    {
        Debug.Log("[Test] Sending NPC_INTERACT...");
        NetworkManager.Instance.InteractNpc(1);
    }

    void TestEnhance()
    {
        Debug.Log("[Test] Sending ENHANCE_REQ...");
        NetworkManager.Instance.RequestEnhance(0);
    }

    void TestTutorial()
    {
        Debug.Log("[Test] Sending TUTORIAL_STEP_COMPLETE...");
        NetworkManager.Instance.CompleteTutorialStep(1);
    }

    void PrintSummary()
    {
        int total = _passCount + _failCount;
        if (_failCount == 0)
            Debug.Log($"[Test] ═══ Phase 2 Result: ALL PASS ({_passCount}/{total}) ═══");
        else
            Debug.LogError($"[Test] ═══ Phase 2 Result: {_failCount} FAIL, {_passCount} PASS / {total} total ═══");
    }

    void LogResult(string testName, bool pass, string detail)
    {
        if (pass)
        {
            _passCount++;
            Debug.Log($"[Test][PASS] {testName}: {detail}");
        }
        else
        {
            _failCount++;
            Debug.LogError($"[Test][FAIL] {testName}: {detail}");
        }
    }
}
