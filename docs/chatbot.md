  Sau khi nghiên cứu kỹ, tôi sẽ trình bày bức tranh thực tế về các vấn đề khi xây dựng hệ thống này, cùng với giải pháp khả thi.

  ---
  PHẦN 1: VẤN ĐỀ THỰC TẾ (EDGE CASES)

  1. 8 Failure Modes "vô hình" trong chatbot (78% total failures) [1]

  ┌───────────────────────────┬───────┬─────────────────────────────────┬────────────────────────────────────────────┐
  │       Failure Mode        │   %   │              Mô tả              │                   Ví dụ                    │
  ├───────────────────────────┼───────┼─────────────────────────────────┼────────────────────────────────────────────┤
  │ The Confidence Trap       │ 26.4% │ AI trả lời sai nhưng tự tin     │ "Bạn cần đặt hotel 5 sao" → user cần 3 sao │
  ├───────────────────────────┼───────┼─────────────────────────────────┼────────────────────────────────────────────┤
  │ The Drift                 │ 37.2% │ AI lạc đề nhưng vẫn "hợp lý"    │ User hỏi giá → AI giải thích tính năng     │
  ├───────────────────────────┼───────┼─────────────────────────────────┼────────────────────────────────────────────┤
  │ The Silent Mismatch       │ 9.0%  │ AI hiểu sai nhưng không hỏi lại │ "1 người" → user nói "2 người"             │
  ├───────────────────────────┼───────┼─────────────────────────────────┼────────────────────────────────────────────┤
  │ The Death Spiral          │ 6.9%  │ Lặp vòng không tiến triển       │ Hỏi đi hỏi lại cùng 1 câu                  │
  ├───────────────────────────┼───────┼─────────────────────────────────┼────────────────────────────────────────────┤
  │ The Contradiction Unravel │ 7.6%  │ AI tự mâu thuẫn                 │ "Không có phí" → "Phí 10%"                 │
  ├───────────────────────────┼───────┼─────────────────────────────────┼────────────────────────────────────────────┤
  │ The Walkaway              │ 5.9%  │ User bỏ đi không báo            │ User stop replying                         │
  ├───────────────────────────┼───────┼─────────────────────────────────┼────────────────────────────────────────────┤
  │ The Partial Recovery      │ 6.3%  │ Thành công một phần             │ Lấy được email nhưng sai phone             │
  ├───────────────────────────┼───────┼─────────────────────────────────┼────────────────────────────────────────────┤
  │ The Mystery Failure       │ 12.0% │ Thất bại không rõ lý do         │ -                                          │
  └───────────────────────────┴───────┴─────────────────────────────────┴────────────────────────────────────────────┘

  Bài học: Graph phải detect được các state này và có transition để thoát.

  ---
  2. Vấn đề Multi-turn Conversation

  Nghiên cứu Microsoft/Salesforce (2025) [2]:
  - 39% giảm performance sau 5+ turns
  - 112% tăng độ không ổn định (variance giữa best/worst case)
  - Loss of middle turns: Information ở giữa conversation bị "quên"

  Root causes:
  User: "Tôi muốn đặt tour 3 ngày 2 đêm cho 2 người, ngân sách 5 triệu"
        ↓ (AI bỏ qua "2 người", "5 triệu")
  AI: "Chúng tôi có tour 3 ngày 2 đêm giá 6 triệu"
        ↓
  User: "Đắt quá, có nào dưới 5 triệu không?"
        ↓ (AI không nhớ đã nói "2 người")
  AI: "Tour cho 1 người dưới 5 triệu có..."

  ---
  3. Multi-Intent & Context Switching [1]

  Case A: User switch đề tài giữa diagnostic flow
  AI: "Bạn có triệu chứng gì?"
  User: "Đau đầu, mệt mỏi... mà shop có giao hàng tận nơi không?"
  AI: ??? → Phải pause diagnostic flow, trả lời câu hỏi, rồi resume

  Case B: User gộp nhiều thông tin 1 tin nhắn
  AI: "Bạn cần đặt cho mấy người?"
  User: "2 người lớn, 1 trẻ em 5 tuổi, ngày 15/3, khách sạn 4 sao"
        ↓ (State machine chỉ expect 1 số)
  AI: ??? → Phải parse tất cả cùng lúc

  Case C: Ambiguous edge cases
  User: "Hủy cho tôi"
        ↓ Hủy gì? Order? Reservation? Subscription?
  AI phải ask-back → nhưng 10-15% trường hợp vẫn miss [1]

  ---
  4. The Intent Gap (32% dissatisfactory responses) [1]

  4 layers của user intent:
  1. Immediate desires (literal): "Cho tôi giá tour"
  2. Final goals (deeper): "So sánh các option trước khi quyết định"
  3. Background desiderata (unstated): "Không muốn bị spam sau khi hỏi"
  4. Autonomy: "Tôi muốn tự quyết định, không bị push sale"

  LLM giỏi ở #1, nhưng thường vi phạm #2-4.

  ---
  5. State Management Challenges [3][4]

  ┌───────────────────────────┬────────────────────────────────────┬───────────────────────────────────┐
  │          Vấn đề           │               Mô tả                │              Impact               │
  ├───────────────────────────┼────────────────────────────────────┼───────────────────────────────────┤
  │ Token explosion           │ 50+ turns → 10K+ tokens            │ Cost tăng 4x, latency 2s→8s       │
  ├───────────────────────────┼────────────────────────────────────┼───────────────────────────────────┤
  │ Context rot               │ "Lost-in-the-middle" effect        │ 30%+ accuracy drop ở giữa context │
  ├───────────────────────────┼────────────────────────────────────┼───────────────────────────────────┤
  │ Summary drift             │ Summary của summary → sai tích lũy │ "2 người" → "1 người" sau 5 turns │
  ├───────────────────────────┼────────────────────────────────────┼───────────────────────────────────┤
  │ Session isolation failure │ User mở 2 conversation song song   │ State bị trộn lẫn                 │
  ├───────────────────────────┼────────────────────────────────────┼───────────────────────────────────┤
  │ Premature compression     │ Nén quá sớm → mất info quan trọng  │ Slot values bị drop               │
  └───────────────────────────┴────────────────────────────────────┴───────────────────────────────────┘

  ---
  PHẦN 2: GIẢI PHÁP ĐỀ XUẤT

  Kiến trúc khả thi: Hybrid Conversation Graph

  ┌─────────────────────────────────────────────────────────┐
  │                   LLM (Generative Layer)                │
  │  - Natural language understanding                       │
  │  - Response generation                                  │
  │  - Ambiguity detection                                  │
  └─────────────────────────────────────────────────────────┘
                            ↕
  ┌─────────────────────────────────────────────────────────┐
  │              Graph State Machine (Control Layer)         │
  │  ┌──────────┐  ┌──────────┐  ┌──────────┐              │
  │  │  Intent  │→ │ Response │→ │Transition│              │
  │  │  Nodes   │  │  Nodes   │  │  Edges   │              │
  │  └──────────┘  └──────────┘  └──────────┘              │
  │  - Valid paths enforced                                │
  │  - State persistence (checkpointing)                   │
  │  - Guardrails cho high-stakes actions                  │
  └─────────────────────────────────────────────────────────┘
                            ↕
  ┌─────────────────────────────────────────────────────────┐
  │              Persistent Store (Memory Layer)            │
  │  - Session state (Redis/Postgres)                       │
  │  - User preferences                                     │
  │  - Conversation history (compressed)                    │
  └─────────────────────────────────────────────────────────┘

  ---
  Graph Schema đề xuất

  {
    "nodes": [
      {
        "id": "intent_greeting",
        "type": "intent",
        "label": "User greets",
        "triggers": ["xin chào", "hi", "hello", "alo"],
        "confidence_threshold": 0.7
      },
      {
        "id": "resp_welcome_casual",
        "type": "response",
        "label": "Casual welcome",
        "templates": ["Chào bạn! Cần mình giúp gì?", "Hi! Có gì hot?"],
        "tone": "casual",
        "context": ["general", "support"]
      },
      {
        "id": "state_collecting_info",
        "type": "state",
        "label": "Collecting user info",
        "required_slots": ["name", "phone"],
        "optional_slots": ["email", "address"]
      },
      {
        "id": "failure_ambiguity_detected",
        "type": "failure_state",
        "label": "Ambiguous input",
        "recovery_path": "ask_clarification"
      }
    ],
    "edges": [
      {
        "source": "intent_greeting",
        "target": "resp_welcome_casual",
        "relation": "triggers",
        "weight": 1.0
      },
      {
        "source": "resp_welcome_casual",
        "target": "state_collecting_info",
        "relation": "leads_to",
        "condition": "user_shows_interest"
      },
      {
        "source": "intent_greeting",
        "target": "failure_ambiguity_detected",
        "relation": "can_become",
        "condition": "confidence < 0.7"
      },
      {
        "source": "failure_ambiguity_detected",
        "target": "ask_clarification",
        "relation": "requires_recovery",
        "max_retries": 2
      }
    ]
  }

  ---
  Xử lý Edge Cases trong Graph

  1. Multi-Intent Detection:
  # Graph query: tìm tất cả intents match với input
  matches = graph.query("""
      MATCH (n:Intent)
      WHERE n.triggers CONTAINS $input_tokens
      RETURN n ORDER BY n.confidence DESC LIMIT 3
  """)
  if len(matches) > 1:
      # Multiple intents detected → ambiguity
      current_state = "failure_ambiguity_detected"
      transition_to("ask_clarification")

  2. Context Switching:
  # Lưu current_path trong session state
  session["active_path"] = ["greeting", "collecting_info", "booking"]

  # User hỏi unrelated question
  if new_intent not in current_path_neighbors:
      # Soft pause: lưu vị trí hiện tại
      session["paused_at"] = session["active_path"]
      session["paused_ttl"] = now() + 12h
      # Switch sang path mới
      session["active_path"] = [new_intent]

  3. State Persistence (LangGraph-style checkpointing) [5]:
  # Mỗi turn lưu 1 checkpoint
  checkpoint = {
      "turn_id": 42,
      "current_node": "collecting_info",
      "collected_slots": {"name": "An", "phone": "0123..."},
      "path_history": ["greeting", "product_inquiry", "collecting_info"],
      "failure_count": 0,
      "timestamp": "2026-04-23T10:30:00Z"
  }
  db.checkpoints.insert(session_id, checkpoint)

  4. Context Compression Strategy [3]:
  # Trigger compression ở 80% token budget
  if token_count > 0.8 * MAX_TOKENS:
      # Nén turns cũ, giữ lại slots quan trọng
      compressed = llm.summarize(
          turns[:-5],  # Giữ 5 turns mới nhất nguyên vẹn
          required_fields=["collected_slots", "current_goal"]
      )
      conversation_history = [compressed] + turns[-5:]

  ---
  PHẦN 3: TÍCH HỢP VỚI NEXO

  Cách nexo có thể giúp

  1. Graph Generation từ Template Files:

  # nexo/extract_conversation.py
  def extract_conversation_templates(path: Path) -> dict:
      """
      Đọc file .md/.json conversation templates
      Output: nodes + edges dict
      """
      nodes = []
      edges = []

      # Parse intent definitions
      for template in templates:
          nodes.append({
              "id": f"intent_{template.id}",
              "type": "intent",
              "label": template.name,
              "source_file": str(path)
          })

          # Extract transitions
          for transition in template.transitions:
              edges.append({
                  "source": f"intent_{template.id}",
                  "target": f"response_{transition.target}",
                  "relation": "leads_to"
              })

      return {"nodes": nodes, "edges": edges}

  2. MCP Tools cho Chatbot:

  # nexo/serve.py - MCP server tools
  @mcp.tool()
  async def conversation_patterns(query: str) -> list:
      """Query conversation pattern graph"""
      subgraph = query_graph(graph_path, query)
      return format_patterns(subgraph)

  @mcp.tool()
  async def next_valid_states(current_state: str, user_input: str) -> list:
      """Get valid next states from current position"""
      return get_neighbors(graph_path, current_state, user_input)

  @mcp.tool()
  async def detect_ambiguity(user_input: str) -> dict:
      """Check if input matches multiple intents"""
      matches = match_intents(graph_path, user_input)
      return {
          "is_ambiguous": len(matches) > 1,
          "candidates": matches
      }

  3. Query Examples:

  # Tìm escalation paths
  nexo query "Đường dẫn xử lý khách hàng giận là gì?"
  # → Returns: complaint → apologize → offer_resolution → [resolved/handoff]

  # Tìm patterns cho use case cụ thể
  nexo query "Patterns cho onboarding user mới"
  # → Returns subgraph: greeting → explain_features → collect_preferences → welcome_complete

  # Check ambiguity
  nexo query "Input 'hủy cho tôi' match với những intents nào?"
  # → Returns: [cancel_order, cancel_subscription, cancel_reservation]

  ---
  PHẦN 4: KẾ HOẠCH TRIỂN KHAI

  Phase 1: MVP (2-3 tuần)

  ┌────────────────────┬─────────────────────────────────────────────────────────┐
  │        Task        │                       Description                       │
  ├────────────────────┼─────────────────────────────────────────────────────────┤
  │ 1. Template format │ Định nghĩa YAML schema cho conversation templates       │
  ├────────────────────┼─────────────────────────────────────────────────────────┤
  │ 2. Extractor       │ Viết extract_conversation_templates() trong nexo        │
  ├────────────────────┼─────────────────────────────────────────────────────────┤
  │ 3. Graph schema    │ Thêm node types: intent, response, state, failure_state │
  ├────────────────────┼─────────────────────────────────────────────────────────┤
  │ 4. Basic queries   │ Implement query_patterns(), find_path()                 │
  └────────────────────┴─────────────────────────────────────────────────────────┘

  Phase 2: Edge Case Handling (2-3 tuần)

  ┌───────────────────────────┬───────────────────────────────────────────┐
  │           Task            │                Description                │
  ├───────────────────────────┼───────────────────────────────────────────┤
  │ 5. Multi-intent detection │ Query multiple matches, flag ambiguity    │
  ├───────────────────────────┼───────────────────────────────────────────┤
  │ 6. State persistence      │ Session checkpointing (SQLite/Redis)      │
  ├───────────────────────────┼───────────────────────────────────────────┤
  │ 7. Recovery paths         │ Define failure states và transition rules │
  ├───────────────────────────┼───────────────────────────────────────────┤
  │ 8. Context compression    │ Implement summarization strategy          │
  └───────────────────────────┴───────────────────────────────────────────┘

  Phase 3: Production Integration (2-3 tuần)

  ┌───────────────────────┬──────────────────────────────────────────────────────┐
  │         Task          │                     Description                      │
  ├───────────────────────┼──────────────────────────────────────────────────────┤
  │ 9. MCP server         │ Expose tools cho AI chatbot                          │
  ├───────────────────────┼──────────────────────────────────────────────────────┤
  │ 10. Monitoring        │ Track fallback rate, ambiguity rate, drop-off points │
  ├───────────────────────┼──────────────────────────────────────────────────────┤
  │ 11. Dashboard         │ Visualize conversation flows, failure hotspots       │
  ├───────────────────────┼──────────────────────────────────────────────────────┤
  │ 12. Testing framework │ Test conversation paths, edge cases                  │
  └───────────────────────┴──────────────────────────────────────────────────────┘

  ---
  PHẦN 5: RỦI RO & MITIGATION

  ┌────────────────────────────────┬──────────────────────────┬───────────────────────────────────────────────────────┐
  │              Risk              │          Impact          │                      Mitigation                       │
  ├────────────────────────────────┼──────────────────────────┼───────────────────────────────────────────────────────┤
  │ Graph quá phức tạp             │ Khó maintain, query chậm │ Giới hạn max depth=5, max neighbors=10                │
  ├────────────────────────────────┼──────────────────────────┼───────────────────────────────────────────────────────┤
  │ Template không cover hết cases │ Fallback rate cao        │ Có fallback path → LLM pure + log để improve template │
  ├────────────────────────────────┼──────────────────────────┼───────────────────────────────────────────────────────┤
  │ State management bug           │ User bị kẹt trong loop   │ Timeout + auto-handoff sau 3 retries                  │
  ├────────────────────────────────┼──────────────────────────┼───────────────────────────────────────────────────────┤
  │ Token cost cao                 │ Budget vượt              │ Compression ở 80%, sliding window 10 turns            │
  ├────────────────────────────────┼──────────────────────────┼───────────────────────────────────────────────────────┤
  │ Ambiguity detection fail       │ User experience tệ       │ Conservative threshold (0.7), ask-back khi doubt      │
  └────────────────────────────────┴──────────────────────────┴───────────────────────────────────────────────────────┘

  ---
  KẾT LUẬN

  Giải pháp đề xuất: Hybrid Conversation Graph với 3 layers:
  1. LLM cho flexibility (NLU, generation)
  2. Graph State Machine cho control (valid paths, guardrails)
  3. Persistent Store cho state management

  Nexo's role: Build và query graph từ template files, expose qua MCP tools.

  Bạn muốn tôi implement prototype phase nào trước?

  ---
  Sources:

  [1] https://pub.towardsai.net/intent-classification-isnt-enough-failure-modes-in-a-whatsapp-llm-pipeline-that-had-to-ask-before-213
  1e1df13ef

  [2] https://tianpan.co/blog/2026-04-10-intent-gap-llm-applications

  [3] https://www.youngju.dev/blog/chatbot/2026-03-04-chatbot-multi-turn-context-management-2026.en

  [4] https://zylos.ai/research/2026-03-31-context-window-management-session-lifecycle-long-running-agents

  [5] https://www.mmntm.net/articles/orchestration-showdown