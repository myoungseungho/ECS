// ━━━ MentorShopUI.cs ━━━
// 사제 기여도 상점 UI (S056 TASK 18)
// MentorManager.OnMentorShopOpened/Closed 이벤트 기반

using System;
using UnityEngine;

public class MentorShopUI : MonoBehaviour
{
    // ━━━ 싱글톤 ━━━
    public static MentorShopUI Instance { get; private set; }

    // ━━━ 상태 ━━━
    private bool _isVisible;
    private string _statusText = "";

    private void Awake()
    {
        if (Instance != null && Instance != this)
        {
            Destroy(gameObject);
            return;
        }
        Instance = this;
    }

    private void Start()
    {
        var mm = MentorManager.Instance;
        if (mm != null)
        {
            mm.OnMentorShopOpened += HandleShopOpened;
            mm.OnMentorShopClosed += HandleShopClosed;
            mm.OnShopListReceived += HandleShopListReceived;
            mm.OnShopBuyResult += HandleShopBuyResult;
        }
    }

    private void OnDestroy()
    {
        var mm = MentorManager.Instance;
        if (mm != null)
        {
            mm.OnMentorShopOpened -= HandleShopOpened;
            mm.OnMentorShopClosed -= HandleShopClosed;
            mm.OnShopListReceived -= HandleShopListReceived;
            mm.OnShopBuyResult -= HandleShopBuyResult;
        }
        if (Instance == this) Instance = null;
    }

    // ━━━ 핸들러 ━━━

    private void HandleShopOpened()
    {
        _isVisible = true;
        _statusText = "";
    }

    private void HandleShopClosed()
    {
        _isVisible = false;
    }

    private void HandleShopListReceived(Network.MentorShopListData data)
    {
        _statusText = "";
    }

    private void HandleShopBuyResult(Network.MentorShopBuyResultData data)
    {
        if (data.Result == Network.MentorShopBuyResult.SUCCESS)
            _statusText = $"구매 성공! 잔여 기여도: {data.RemainingContribution}";
        else if (data.Result == Network.MentorShopBuyResult.INSUFFICIENT_CONTRIB)
            _statusText = "기여도 부족";
        else
            _statusText = "구매 실패";
    }

    // ━━━ OnGUI ━━━

    private void OnGUI()
    {
        if (!_isVisible) return;

        float w = 380f, h = 420f;
        float x = (Screen.width - w) / 2f + 220f;
        float y = (Screen.height - h) / 2f;

        GUI.Box(new Rect(x, y, w, h), "");
        GUILayout.BeginArea(new Rect(x + 10, y + 10, w - 20, h - 20));

        var mm = MentorManager.Instance;
        uint contrib = mm != null ? mm.Contribution : 0;

        GUILayout.Label("<b>기여도 상점</b>", new GUIStyle(GUI.skin.label) { fontSize = 16, richText = true });
        GUILayout.Label($"보유 기여도: <color=cyan>{contrib}</color>", new GUIStyle(GUI.skin.label) { richText = true });
        GUILayout.Space(5);

        if (!string.IsNullOrEmpty(_statusText))
        {
            GUILayout.Label(_statusText);
            GUILayout.Space(5);
        }

        // 상점 아이템 목록
        var items = mm?.ShopItems;
        if (items != null && items.Length > 0)
        {
            for (int i = 0; i < items.Length; i++)
            {
                var item = items[i];
                GUILayout.BeginHorizontal();
                GUILayout.Label($"{item.Name} (비용: {item.Cost})", GUILayout.Width(260));
                if (GUILayout.Button("구매", GUILayout.Width(80)))
                {
                    mm?.BuyShopItem(item.ItemId);
                }
                GUILayout.EndHorizontal();
            }
        }
        else
        {
            GUILayout.Label("상점 정보 로딩 중...");
        }

        GUILayout.FlexibleSpace();

        if (GUILayout.Button("갱신"))
            mm?.RequestShopList();

        if (GUILayout.Button("닫기"))
            mm?.CloseMentorShop();

        GUILayout.EndArea();
    }
}
