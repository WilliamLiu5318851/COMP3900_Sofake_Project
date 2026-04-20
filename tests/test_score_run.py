import pytest
from unittest.mock import patch, MagicMock
from backend.main import _score_run

@patch("backend.main.httpx.Client.post")
def test_score_run_mapping(mock_post):
    """
    Validate the _score_run function in backend/main.py.
    Ensure it maps the correct texts for FUSE evaluation (vs Ground Truth & vs Parent).
    """
    # Create a dummy run_log with a clear lineage: 
    # Ground truth -> Post A (by Alex) -> Post B (by Blake replying to Post A)
    dummy_run_log = {
        "steps": [
            {
                "step": 1,
                "events": [{
                    "action": "new_post",
                    "agent_name": "Alex",
                    "new_post_id": "post_A",
                    "new_post_text": "This is Post A text",
                    "source_post_id": "ground_truth"
                }]
            },
            {
                "step": 2,
                "events": [{
                    "action": "reply",
                    "agent_name": "Blake",
                    "new_post_id": "post_B",
                    "new_post_text": "This is Post B text",
                    "source_post_id": "post_A"
                }]
            }
        ]
    }
    
    # Mock FUSE responses
    mock_resp = MagicMock()
    mock_resp.status_code = 200
    mock_resp.json.return_value = {"Total_Deviation": 5.0}
    mock_post.return_value = mock_resp
    
    ground_truth_text = "This is ground truth"
    
    # Call _score_run
    _score_run(dummy_run_log, ground_truth_text)
    
    # Assertions
    assert mock_post.call_count == 3
    call_args_list = mock_post.call_args_list
    
    # Call 1: Evaluating Post A vs Ground Truth
    args1, kwargs1 = call_args_list[0]
    assert kwargs1["json"]["original"] == ground_truth_text
    assert kwargs1["json"]["evolved"] == "This is Post A text"
    
    # Call 2: Evaluating Post B vs Ground Truth
    args2, kwargs2 = call_args_list[1]
    assert kwargs2["json"]["original"] == ground_truth_text
    assert kwargs2["json"]["evolved"] == "This is Post B text"
    
    # Call 3: Evaluating Post B vs Parent Post (Post A)
    args3, kwargs3 = call_args_list[2]
    assert kwargs3["json"]["original"] == "This is Post A text"
    assert kwargs3["json"]["evolved"] == "This is Post B text"