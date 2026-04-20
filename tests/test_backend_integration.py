import pytest
import httpx
from fastapi.testclient import TestClient
from unittest.mock import patch, MagicMock
from backend.main import app

client = TestClient(app)
orig_post = httpx.Client.post

# ── 1. 测试全流程：Simulation -> FUSE -> Save to DB ──────────────────────────────

@patch("backend.main.get_news_by_id")
@patch("backend.main.insert_simulation_run")
@patch("backend.main.httpx.Client.post", autospec=True)
def test_simulate_endpoint_full_pipeline(mock_post, mock_insert, mock_get_news):
    """
    测试 /api/simulate 接口的完整生命周期：
    1. 成功调用 Agent 拿到多路并行数据
    2. 成功调用 FUSE 拿到分析分数
    3. 成功组装数据返回给前端展示
    4. 成功调用数据库 insert 方法，且保存的数据里包含正确的 parallel run 数量！
    """
    # Mock database fetching ground truth
    mock_get_news.return_value = (1, "This is the ground truth")

    # Mock httpx responses to AGENT and FUSE services
    def side_effect(*args, **kwargs):
        url = kwargs.get("url")
        if not url and len(args) > 0:
            for arg in args:
                if isinstance(arg, str):
                    url = arg
                    break
        url_str = str(url).lower() if url else ""
        
        if "agent" in url_str or "8001" in url_str:
            mock_resp = MagicMock()
            mock_resp.status_code = 200
            # 模拟 Agent 服务返回 2 个 Parallel Runs
            mock_resp.json.return_value = {
                "runs": [
                    {
                        "run_log": {"steps": [{"step": 1, "events": [{"action": "new_post", "agent_name": "Alex", "new_post_id": "post_A", "new_post_text": "Text 1", "source_post_id": "ground_truth"}]}]}, 
                        "signal_drift": {}
                    },
                    {
                        "run_log": {"steps": [{"step": 1, "events": [{"action": "new_post", "agent_name": "Blake", "new_post_id": "post_B", "new_post_text": "Text 2", "source_post_id": "ground_truth"}]}]}, 
                        "signal_drift": {}
                    }
                ]
            }
            return mock_resp
        elif "fuse" in url_str or "8002" in url_str:
            mock_resp = MagicMock()
            mock_resp.status_code = 200
            # 模拟 FUSE 服务返回完整的 9 维度数据
            mock_resp.json.return_value = {
                "Total_Deviation": 5.0, 
                "Extended_Deviation": 4.5,
                "SS": 2.0, "NII": 3.0, "CS": 4.0, "STS": 5.0, "TS": 1.0, 
                "PD": 6.0, "SI": 7.0, "SAA": 8.0, "PIB": 9.0
            }
            return mock_resp
        else:
            return orig_post(*args, **kwargs)
        
    mock_post.side_effect = side_effect

    # 前端发起请求：要求跑 2 个 parallel simulations
    response = client.post("/api/simulate", json={"news_id": 1, "simulations": 2})

    # --- 断言 1: 前端是否能成功拿到 200 OK 且包含数据？ ---
    assert response.status_code == 200
    data = response.json()
    assert "runs" in data
    assert len(data["runs"]) == 2
    
    # --- 断言 2: FUSE 数据收集与分析是否正确映射？ ---
    for run in data["runs"]:
        assert "fuse_evaluations" in run
        assert isinstance(run["fuse_evaluations"], list)
        assert len(run["fuse_evaluations"]) > 0
        assert run["fuse_evaluations"][0]["fuse_scores_vs_ground_truth"]["Total_Deviation"] == 5.0

    # --- 断言 3: (核心) 验证后台是否成功将 Parallel Run 数据 Save 进数据库？ ---
    mock_insert.assert_called_once()
    args, kwargs = mock_insert.call_args
    
    # insert_simulation_run 的最后一个参数是 result_json
    saved_result_json = args[-1] if len(args) > 0 else kwargs.get("result_json")
    
    assert saved_result_json is not None, "后台没有把 result_json 传给数据库！"
    assert "runs" in saved_result_json, "存入数据库的数据丢失了 parallel runs！"
    assert len(saved_result_json["runs"]) == 2, "存入数据库的 parallel runs 数量错误！"
    assert "fuse_evaluations" in saved_result_json["runs"][0], "存入数据库的 Run 丢失了 FUSE 分数！"


# ── 2. 测试历史记录拉取：确保前端 Saved Runs 页面能正常工作 ────────────────────

@patch("backend.main.list_history_runs")
def test_history_list_endpoint(mock_list):
    """测试前端获取 Saved Runs 列表功能"""
    mock_list.return_value = [
        {"run_id": 1, "created_at": "2026-04-18", "news_id": 1}
    ]
    
    response = client.get("/api/history")
    assert response.status_code == 200
    assert isinstance(response.json(), list)
    assert len(response.json()) == 1
    assert response.json()[0]["run_id"] == 1


@patch("backend.main.get_history_run_detail")
def test_history_detail_endpoint_with_parallel_data(mock_detail):
    """测试前端点击特定 Run 时，获取到的详情里是否包含正确的 Parallel Runs 数据"""
    mock_detail.return_value = {
        "run_id": 1,
        "content": "This is ground truth",
        "result_json": {
            "run_log": {},
            "runs": [
                {"run_log": {"run_id": "run00"}, "fuse_evaluations": []},
                {"run_log": {"run_id": "run01"}, "fuse_evaluations": []}
            ]
        }
    }
    
    response = client.get("/api/history/1")
    assert response.status_code == 200
    
    data = response.json()
    assert data["run_id"] == 1
    assert "result_json" in data
    
    # 确保从数据库返回给前端展示的数据，确实能包含多个 Parallel Runs 结构
    assert "runs" in data["result_json"]
    assert len(data["result_json"]["runs"]) == 2