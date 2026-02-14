// ━━━ BountyUI.cs ━━━
// 강호 현상금 UI — 일일/주간 현상금 표시, 수락/완료, 랭킹, PvP 현상금 알림
// BountyManager 이벤트 구독 (B키 토글)

using UnityEngine;
using UnityEngine.UI;
using Network;

public class BountyUI : MonoBehaviour
{
    // ━━━ UI 참조 (Start에서 코드 생성) ━━━
    private GameObject _panel;
    private Text _titleText;
    private Text _bountyListText;
    private Text _statusText;
    private Text _rankingText;
    private Button _refreshButton;
    private Button _rankingButton;

    private bool _showRanking;

    private void Start()
    {
        BuildUI();

        if (BountyManager.Instance != null)
        {
            BountyManager.Instance.OnBountyListChanged += HandleListChanged;
            BountyManager.Instance.OnAcceptResult += HandleAcceptResult;
            BountyManager.Instance.OnCompleteResult += HandleCompleteResult;
            BountyManager.Instance.OnRankingReceived += HandleRanking;
            BountyManager.Instance.OnPvPBountyAlert += HandlePvPBounty;
            BountyManager.Instance.OnPanelOpened += ShowPanel;
            BountyManager.Instance.OnPanelClosed += HidePanel;
        }

        if (_panel != null) _panel.SetActive(false);
    }

    private void OnDestroy()
    {
        if (BountyManager.Instance != null)
        {
            BountyManager.Instance.OnBountyListChanged -= HandleListChanged;
            BountyManager.Instance.OnAcceptResult -= HandleAcceptResult;
            BountyManager.Instance.OnCompleteResult -= HandleCompleteResult;
            BountyManager.Instance.OnRankingReceived -= HandleRanking;
            BountyManager.Instance.OnPvPBountyAlert -= HandlePvPBounty;
            BountyManager.Instance.OnPanelOpened -= ShowPanel;
            BountyManager.Instance.OnPanelClosed -= HidePanel;
        }
    }

    private void Update()
    {
        // B키로 현상금 패널 토글
        if (Input.GetKeyDown(KeyCode.B))
        {
            if (BountyManager.Instance != null)
            {
                if (BountyManager.Instance.IsPanelOpen)
                    BountyManager.Instance.ClosePanel();
                else
                    BountyManager.Instance.OpenPanel();
            }
        }

        // ESC로 닫기
        if (_panel != null && _panel.activeSelf && Input.GetKeyDown(KeyCode.Escape))
        {
            BountyManager.Instance?.ClosePanel();
        }

        // 패널 열린 상태에서 숫자키로 수락/완료
        if (_panel != null && _panel.activeSelf && !_showRanking)
        {
            // 1~3: 일일 현상금 수락
            for (int i = 0; i < 3; i++)
            {
                if (Input.GetKeyDown(KeyCode.Alpha1 + i))
                {
                    if (BountyManager.Instance != null && i < BountyManager.Instance.DailyBounties.Count)
                    {
                        var bounty = BountyManager.Instance.DailyBounties[i];
                        if (bounty.Accepted == 0)
                            BountyManager.Instance.AcceptBounty(bounty.BountyId);
                        else if (bounty.Completed == 0)
                            BountyManager.Instance.CompleteBounty(bounty.BountyId);
                    }
                }
            }

            // 4: 주간 현상금 수락/완료
            if (Input.GetKeyDown(KeyCode.Alpha4))
            {
                if (BountyManager.Instance != null && BountyManager.Instance.HasWeekly)
                {
                    var bounty = BountyManager.Instance.WeeklyBounty;
                    if (bounty.Accepted == 0)
                        BountyManager.Instance.AcceptBounty(bounty.BountyId);
                    else if (bounty.Completed == 0)
                        BountyManager.Instance.CompleteBounty(bounty.BountyId);
                }
            }

            // R: 랭킹 탭
            if (Input.GetKeyDown(KeyCode.R))
            {
                _showRanking = true;
                BountyManager.Instance?.RequestRanking();
            }
        }

        // 랭킹 탭에서 Backspace로 돌아가기
        if (_panel != null && _panel.activeSelf && _showRanking)
        {
            if (Input.GetKeyDown(KeyCode.Backspace))
            {
                _showRanking = false;
                RefreshDisplay();
            }
        }
    }

    // ━━━ UI 구성 (코드 생성) ━━━

    private void BuildUI()
    {
        // Panel
        _panel = new GameObject("BountyPanel");
        _panel.transform.SetParent(transform, false);
        var panelRT = _panel.AddComponent<RectTransform>();
        panelRT.anchorMin = new Vector2(0.1f, 0.05f);
        panelRT.anchorMax = new Vector2(0.9f, 0.95f);
        panelRT.offsetMin = Vector2.zero;
        panelRT.offsetMax = Vector2.zero;
        var panelBg = _panel.AddComponent<Image>();
        panelBg.color = new Color(0.08f, 0.05f, 0.02f, 0.95f);

        // Title
        var titleGo = CreateText(_panel.transform, "Title", "Bounty Board",
            new Vector2(0.5f, 1f), new Vector2(0.5f, 1f), new Vector2(0, -10), new Vector2(300, 35));
        _titleText = titleGo.GetComponent<Text>();
        _titleText.fontSize = 22;
        _titleText.fontStyle = FontStyle.Bold;
        _titleText.alignment = TextAnchor.MiddleCenter;
        _titleText.color = new Color(1f, 0.85f, 0.4f);
        var titleRT = titleGo.GetComponent<RectTransform>();
        titleRT.pivot = new Vector2(0.5f, 1f);

        // Subtitle (instructions)
        var subGo = CreateText(_panel.transform, "Subtitle",
            "[1-3] Daily  |  [4] Weekly  |  [R] Ranking  |  [B] Close",
            new Vector2(0.5f, 1f), new Vector2(0.5f, 1f), new Vector2(0, -42), new Vector2(600, 22));
        var subText = subGo.GetComponent<Text>();
        subText.fontSize = 12;
        subText.alignment = TextAnchor.MiddleCenter;
        subText.color = new Color(0.7f, 0.7f, 0.6f);
        var subRT = subGo.GetComponent<RectTransform>();
        subRT.pivot = new Vector2(0.5f, 1f);

        // Refresh Button
        var refreshGo = new GameObject("RefreshButton");
        refreshGo.transform.SetParent(_panel.transform, false);
        var refreshRT = refreshGo.AddComponent<RectTransform>();
        refreshRT.anchorMin = new Vector2(1f, 1f);
        refreshRT.anchorMax = new Vector2(1f, 1f);
        refreshRT.pivot = new Vector2(1f, 1f);
        refreshRT.anchoredPosition = new Vector2(-15, -10);
        refreshRT.sizeDelta = new Vector2(80, 28);
        var refreshImg = refreshGo.AddComponent<Image>();
        refreshImg.color = new Color(0.35f, 0.25f, 0.1f);
        _refreshButton = refreshGo.AddComponent<Button>();
        _refreshButton.onClick.AddListener(OnRefreshClicked);
        var refreshTextGo = CreateText(refreshGo.transform, "Text", "Refresh",
            Vector2.zero, Vector2.one, Vector2.zero, Vector2.zero);
        SetFillRT(refreshTextGo);
        refreshTextGo.GetComponent<Text>().alignment = TextAnchor.MiddleCenter;
        refreshTextGo.GetComponent<Text>().fontSize = 12;

        // Ranking Button
        var rankBtnGo = new GameObject("RankingButton");
        rankBtnGo.transform.SetParent(_panel.transform, false);
        var rankBtnRT = rankBtnGo.AddComponent<RectTransform>();
        rankBtnRT.anchorMin = new Vector2(1f, 1f);
        rankBtnRT.anchorMax = new Vector2(1f, 1f);
        rankBtnRT.pivot = new Vector2(1f, 1f);
        rankBtnRT.anchoredPosition = new Vector2(-100, -10);
        rankBtnRT.sizeDelta = new Vector2(80, 28);
        var rankBtnImg = rankBtnGo.AddComponent<Image>();
        rankBtnImg.color = new Color(0.25f, 0.3f, 0.15f);
        _rankingButton = rankBtnGo.AddComponent<Button>();
        _rankingButton.onClick.AddListener(OnRankingClicked);
        var rankTextGo = CreateText(rankBtnGo.transform, "Text", "Ranking",
            Vector2.zero, Vector2.one, Vector2.zero, Vector2.zero);
        SetFillRT(rankTextGo);
        rankTextGo.GetComponent<Text>().alignment = TextAnchor.MiddleCenter;
        rankTextGo.GetComponent<Text>().fontSize = 12;

        // Bounty List Display Area
        var listGo = CreateText(_panel.transform, "BountyList", "Open the Bounty Board to view bounties.",
            new Vector2(0f, 0f), new Vector2(1f, 1f), Vector2.zero, Vector2.zero);
        var listRT = listGo.GetComponent<RectTransform>();
        listRT.anchorMin = new Vector2(0f, 0.06f);
        listRT.anchorMax = new Vector2(1f, 0.88f);
        listRT.offsetMin = new Vector2(15, 0);
        listRT.offsetMax = new Vector2(-15, 0);
        _bountyListText = listGo.GetComponent<Text>();
        _bountyListText.fontSize = 13;
        _bountyListText.alignment = TextAnchor.UpperLeft;

        // Status Text
        var statusGo = CreateText(_panel.transform, "StatusText", "",
            new Vector2(0f, 0f), new Vector2(1f, 0.06f), Vector2.zero, Vector2.zero);
        _statusText = statusGo.GetComponent<Text>();
        _statusText.fontSize = 14;
        _statusText.alignment = TextAnchor.MiddleLeft;
        var statusRT = statusGo.GetComponent<RectTransform>();
        statusRT.anchorMin = new Vector2(0f, 0f);
        statusRT.anchorMax = new Vector2(1f, 0.06f);
        statusRT.offsetMin = new Vector2(15, 0);
        statusRT.offsetMax = new Vector2(-15, 0);
    }

    // ━━━ 이벤트 핸들러 ━━━

    private void HandleListChanged()
    {
        if (!_showRanking) RefreshDisplay();
    }

    private void HandleAcceptResult(BountyAcceptResultData data)
    {
        if (_statusText == null) return;

        if (data.Result == BountyAcceptResult.SUCCESS)
        {
            _statusText.text = $"Bounty #{data.BountyId} accepted!";
            _statusText.color = Color.green;
        }
        else
        {
            _statusText.text = $"Accept failed: {data.Result}";
            _statusText.color = Color.red;
        }
    }

    private void HandleCompleteResult(BountyCompleteData data)
    {
        if (_statusText == null) return;

        if (data.Result == BountyCompleteResult.SUCCESS)
        {
            _statusText.text = $"Bounty #{data.BountyId} completed! Gold:{data.Gold} Exp:{data.Exp} Token:{data.Token}";
            _statusText.color = new Color(1f, 0.85f, 0.4f);
        }
        else
        {
            _statusText.text = $"Complete failed: {data.Result}";
            _statusText.color = Color.red;
        }
    }

    private void HandleRanking(BountyRankingData data)
    {
        if (_bountyListText == null) return;

        _showRanking = true;
        var sb = new System.Text.StringBuilder();
        sb.AppendLine("Bounty Ranking — TOP 10");
        sb.AppendLine("════════════════════════════════════════════════");
        sb.AppendLine("[Backspace] Back to bounties");
        sb.AppendLine();

        for (int i = 0; i < data.Rankings.Length; i++)
        {
            var entry = data.Rankings[i];
            string medal = entry.Rank <= 3 ? (entry.Rank == 1 ? "1st" : entry.Rank == 2 ? "2nd" : "3rd") : $"#{entry.Rank}";
            sb.AppendLine($"  {medal,-6} {entry.Name,-20} Score: {entry.Score}");
        }

        sb.AppendLine();
        sb.AppendLine("────────────────────────────────────────────────");
        sb.AppendLine($"  My Rank: #{data.MyRank}    My Score: {data.MyScore}");

        _bountyListText.text = sb.ToString();
    }

    private void HandlePvPBounty(PvPBountyNotifyData data)
    {
        if (_statusText == null) return;

        string[] tierNames = { "Dangerous", "Wanted", "Villain", "Demon Lord" };
        string tier = data.Tier < tierNames.Length ? tierNames[data.Tier] : $"Tier{data.Tier}";

        _statusText.text = $"PvP Bounty! {data.Name} [{tier}] Streak:{data.KillStreak} Reward:{data.GoldReward}G";
        _statusText.color = new Color(1f, 0.3f, 0.3f);
    }

    private void ShowPanel()
    {
        if (_panel != null) _panel.SetActive(true);
        _showRanking = false;
        RefreshDisplay();
    }

    private void HidePanel()
    {
        if (_panel != null) _panel.SetActive(false);
    }

    // ━━━ UI 갱신 ━━━

    private void RefreshDisplay()
    {
        if (_bountyListText == null || BountyManager.Instance == null) return;

        var dailies = BountyManager.Instance.DailyBounties;
        var sb = new System.Text.StringBuilder();

        sb.AppendLine($"Daily Bounties ({BountyManager.Instance.AcceptedCount}/3 accepted):");
        sb.AppendLine("════════════════════════════════════════════════");

        if (dailies.Count == 0)
        {
            sb.AppendLine("  No bounties available.");
        }
        else
        {
            for (int i = 0; i < dailies.Count; i++)
            {
                var b = dailies[i];
                string status = b.Completed != 0 ? "DONE" : b.Accepted != 0 ? "ACTIVE" : "NEW";
                string statusColor = b.Completed != 0 ? "(Completed)" : b.Accepted != 0 ? "(Press to Complete)" : "(Press to Accept)";
                sb.AppendLine($"  [{i + 1}] #{b.BountyId} — Monster#{b.MonsterId} Lv.{b.Level}  Zone: {b.Zone}");
                sb.AppendLine($"      Reward: {b.Gold}G  {b.Exp}XP  {b.Token}Token  [{status}] {statusColor}");
                sb.AppendLine();
            }
        }

        sb.AppendLine("────────────────────────────────────────────────");

        if (BountyManager.Instance.HasWeekly && BountyManager.Instance.WeeklyBounty != null)
        {
            var w = BountyManager.Instance.WeeklyBounty;
            string status = w.Completed != 0 ? "DONE" : w.Accepted != 0 ? "ACTIVE" : "NEW";
            sb.AppendLine($"  [4] Weekly Boss: #{w.BountyId} — Boss#{w.MonsterId} Lv.{w.Level}  Zone: {w.Zone}");
            sb.AppendLine($"      Reward: {w.Gold}G  {w.Exp}XP  {w.Token}Token  [{status}]");
        }
        else
        {
            sb.AppendLine("  Weekly Boss: Not available (Lv.15+)");
        }

        _bountyListText.text = sb.ToString();
    }

    // ━━━ 버튼 콜백 ━━━

    private void OnRefreshClicked()
    {
        _showRanking = false;
        BountyManager.Instance?.RefreshList();
    }

    private void OnRankingClicked()
    {
        BountyManager.Instance?.RequestRanking();
    }

    // ━━━ 유틸 ━━━

    private static void SetFillRT(GameObject go)
    {
        var rt = go.GetComponent<RectTransform>();
        rt.anchorMin = Vector2.zero;
        rt.anchorMax = Vector2.one;
        rt.offsetMin = Vector2.zero;
        rt.offsetMax = Vector2.zero;
    }

    private static GameObject CreateText(Transform parent, string name, string text,
        Vector2 anchorMin, Vector2 anchorMax, Vector2 anchoredPos, Vector2 sizeDelta)
    {
        var go = new GameObject(name);
        go.transform.SetParent(parent, false);
        var rt = go.AddComponent<RectTransform>();
        rt.anchorMin = anchorMin;
        rt.anchorMax = anchorMax;
        rt.pivot = new Vector2(0f, 1f);
        rt.anchoredPosition = anchoredPos;
        rt.sizeDelta = sizeDelta;

        var t = go.AddComponent<Text>();
        t.text = text;
        t.fontSize = 14;
        t.color = Color.white;
        t.alignment = TextAnchor.UpperLeft;
        t.font = Resources.GetBuiltinResource<Font>("LegacyRuntime.ttf");

        return go;
    }
}
