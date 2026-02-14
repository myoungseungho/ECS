// ━━━ CraftingUI.cs ━━━
// 제작 UI (N키 토글) — 레시피 목록 + 제작 실행 + 결과 표시
// CraftingManager 이벤트 구독

using UnityEngine;
using UnityEngine.UI;

public class CraftingUI : MonoBehaviour
{
    // ━━━ 싱글톤 ━━━
    public static CraftingUI Instance { get; private set; }

    // ━━━ UI 참조 (ProjectSetup에서 코드 생성) ━━━
    [SerializeField] private GameObject _panel;
    [SerializeField] private Text _titleText;
    [SerializeField] private Text _recipeListText;
    [SerializeField] private Text _resultText;

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
        if (CraftingManager.Instance != null)
        {
            CraftingManager.Instance.OnRecipeListChanged += RefreshUI;
            CraftingManager.Instance.OnCraftComplete += HandleCraftResult;
            CraftingManager.Instance.OnCookComplete += HandleCookResult;
            CraftingManager.Instance.OnEnchantComplete += HandleEnchantResult;
            CraftingManager.Instance.OnPanelOpened += ShowPanel;
            CraftingManager.Instance.OnPanelClosed += HidePanel;
        }
        if (_panel != null) _panel.SetActive(false);
    }

    private void OnDestroy()
    {
        if (CraftingManager.Instance != null)
        {
            CraftingManager.Instance.OnRecipeListChanged -= RefreshUI;
            CraftingManager.Instance.OnCraftComplete -= HandleCraftResult;
            CraftingManager.Instance.OnCookComplete -= HandleCookResult;
            CraftingManager.Instance.OnEnchantComplete -= HandleEnchantResult;
            CraftingManager.Instance.OnPanelOpened -= ShowPanel;
            CraftingManager.Instance.OnPanelClosed -= HidePanel;
        }
        if (Instance == this) Instance = null;
    }

    private void Update()
    {
        if (Input.GetKeyDown(KeyCode.N))
        {
            if (CraftingManager.Instance != null)
            {
                if (CraftingManager.Instance.IsPanelOpen)
                    CraftingManager.Instance.ClosePanel();
                else
                    CraftingManager.Instance.OpenPanel();
            }
        }
    }

    // ━━━ UI 갱신 ━━━

    private void RefreshUI()
    {
        if (_recipeListText == null || CraftingManager.Instance == null) return;

        var recipes = CraftingManager.Instance.Recipes;
        var sb = new System.Text.StringBuilder();
        sb.AppendLine($"Recipes ({recipes.Count}):");
        for (int i = 0; i < recipes.Count; i++)
        {
            var r = recipes[i];
            sb.AppendLine($"  [{r.RecipeId}] Prof:{r.Proficiency} Success:{r.SuccessPct}% Gold:{r.Gold} Item:{r.ItemId}x{r.ItemCount}");
        }
        _recipeListText.text = sb.ToString();
    }

    private void HandleCraftResult(Network.CraftResultData data)
    {
        if (_resultText == null) return;

        if (data.Status == Network.CraftResult.SUCCESS)
        {
            string bonus = data.HasBonus > 0 ? " +BONUS!" : "";
            _resultText.text = $"Craft SUCCESS! Item:{data.ItemId} x{data.Count}{bonus}";
            _resultText.color = Color.green;
        }
        else
        {
            _resultText.text = $"Craft FAILED: {data.Status}";
            _resultText.color = Color.red;
        }
    }

    private void HandleCookResult(Network.CookResultData data)
    {
        if (_resultText == null) return;

        if (data.Status == Network.CookResult.SUCCESS)
        {
            _resultText.text = $"Cook SUCCESS! Duration:{data.Duration}s Effects:{data.EffectCount}";
            _resultText.color = Color.green;
        }
        else
        {
            _resultText.text = $"Cook FAILED: {data.Status}";
            _resultText.color = Color.red;
        }
    }

    private void HandleEnchantResult(Network.EnchantResultData data)
    {
        if (_resultText == null) return;

        if (data.Status == Network.EnchantResult.SUCCESS)
        {
            _resultText.text = $"Enchant SUCCESS! Element:{data.Element} Lv{data.Level} (+{data.DamagePct}% dmg)";
            _resultText.color = Color.cyan;
        }
        else
        {
            _resultText.text = $"Enchant FAILED: {data.Status}";
            _resultText.color = Color.red;
        }
    }

    private void ShowPanel()
    {
        if (_panel != null) _panel.SetActive(true);
        RefreshUI();
    }

    private void HidePanel()
    {
        if (_panel != null) _panel.SetActive(false);
    }
}
