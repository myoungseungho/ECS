// ━━━ TestRunner.cs ━━━
// 배치모드에서 TestScene을 로드하고 ConnectionTest를 실행하는 에디터 헬퍼
// Usage: Unity -batchmode -executeMethod TestRunner.RunConnectionTest

using UnityEngine;
using UnityEditor;
using UnityEditor.SceneManagement;

public static class TestRunner
{
    [MenuItem("ECS Game/Run Connection Test", priority = 10)]
    public static void RunConnectionTest()
    {
        Debug.Log("━━━ [TestRunner] TCP 브릿지 연동 테스트 시작 ━━━");

        // TestScene 로드
        var scenePath = "Assets/Scenes/TestScene.unity";
        if (!System.IO.File.Exists(scenePath))
        {
            Debug.LogError("[TestRunner] TestScene.unity 없음! Setup All 먼저 실행하세요.");
            return;
        }

        EditorSceneManager.OpenScene(scenePath);

        // Play 모드 진입
        EditorApplication.isPlaying = true;

        // 15초 후 자동 종료 (배치모드용)
        EditorApplication.update += WaitAndQuit;
        _startTime = EditorApplication.timeSinceStartup;
    }

    private static double _startTime;
    private const double TestDuration = 15.0;

    private static void WaitAndQuit()
    {
        if (EditorApplication.timeSinceStartup - _startTime > TestDuration)
        {
            EditorApplication.update -= WaitAndQuit;
            Debug.Log("━━━ [TestRunner] 테스트 시간 초과 — 종료 ━━━");
            EditorApplication.isPlaying = false;
        }
    }
}
