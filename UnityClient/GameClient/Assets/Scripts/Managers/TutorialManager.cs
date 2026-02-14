// ━━━ TutorialManager.cs ━━━
// 튜토리얼 진행 관리 — 5스텝 보상 시스템
// S033: TUTORIAL_STEP_COMPLETE(330) → TUTORIAL_REWARD(331)

using System;
using System.Collections.Generic;
using UnityEngine;
using Network;

public class TutorialManager : MonoBehaviour
{
    // ━━━ 싱글톤 ━━━
    public static TutorialManager Instance { get; private set; }

    // ━━━ 상태 ━━━
    private HashSet<byte> _completedSteps = new HashSet<byte>();
    private byte _currentStep;

    // ━━━ 이벤트 ━━━
    public event Action<byte> OnStepCompleted;
    public event Action<TutorialRewardData> OnRewardReceived;
    public event Action OnTutorialFinished;

    // ━━━ 프로퍼티 ━━━
    public byte CurrentStep => _currentStep;
    public bool IsComplete => _completedSteps.Count >= 5;

    private const byte MAX_STEPS = 5;

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
        if (NetworkManager.Instance != null)
        {
            NetworkManager.Instance.OnTutorialReward += HandleTutorialReward;
        }
    }

    private void OnDestroy()
    {
        if (NetworkManager.Instance != null)
        {
            NetworkManager.Instance.OnTutorialReward -= HandleTutorialReward;
        }
        if (Instance == this) Instance = null;
    }

    // ━━━ 공개 API ━━━

    /// <summary>현재 스텝 완료 전송</summary>
    public void CompleteCurrentStep()
    {
        if (_currentStep >= MAX_STEPS) return;

        if (NetworkManager.Instance != null)
        {
            NetworkManager.Instance.CompleteTutorialStep(_currentStep);
        }
    }

    /// <summary>특정 스텝 완료 전송</summary>
    public void CompleteStep(byte stepId)
    {
        if (NetworkManager.Instance != null)
        {
            NetworkManager.Instance.CompleteTutorialStep(stepId);
        }
    }

    /// <summary>스텝이 완료되었는지 확인</summary>
    public bool IsStepCompleted(byte stepId)
    {
        return _completedSteps.Contains(stepId);
    }

    // ━━━ 핸들러 ━━━

    private void HandleTutorialReward(TutorialRewardData data)
    {
        _completedSteps.Add(data.StepId);

        if (data.StepId >= _currentStep)
            _currentStep = (byte)(data.StepId + 1);

        OnStepCompleted?.Invoke(data.StepId);
        OnRewardReceived?.Invoke(data);

        Debug.Log($"[Tutorial] Step {data.StepId} complete! Reward: {data.RewardType} x{data.Amount}");

        if (IsComplete)
        {
            OnTutorialFinished?.Invoke();
            Debug.Log("[Tutorial] All steps completed!");
        }
    }
}
