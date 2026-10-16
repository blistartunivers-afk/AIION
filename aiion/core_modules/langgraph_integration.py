"""
aiion/core_modules/langgraph_integration.py
Integración de patrones LangGraph: StateGraph, Checkpointer, Streaming, Interrupts.
"""
import json
import sqlite3
import threading
import time
import uuid
from abc import ABC, abstractmethod
from dataclasses import dataclass, field, asdict
from datetime import datetime
from enum import Enum
from pathlib import Path
from typing import Any, Callable, Dict, List, Optional, TypedDict, Union
from contextlib import contextmanager

# ============================================================================
# TIPOS BASE — State Schema
# ============================================================================

class AgentState(TypedDict, total=False):
    """Estado canónico del agente — compatible con LangGraph"""
    # Input/Output
    user_input: str
    final_response: str
    
    # Conversación
    messages: List[Dict[str, Any]]
    history: List[Dict[str, Any]]
    
    # Contexto
    system_prompt: str
    sensor_context: Dict[str, Any]
    memory_context: str
    cognitive_context: str
    mythos_analysis: Dict[str, Any]
    
    # Ejecución
    current_step: int
    max_steps: int
    tool_calls: List[Dict[str, Any]]
    tool_results: List[Dict[str, Any]]
    thoughts: List[str]
    
    # Control de flujo
    status: str  # "running" | "completed" | "interrupted" | "error" | "awaiting_human"
    error: Optional[str]
    interrupt_reason: Optional[str]
    interrupt_data: Optional[Dict[str, Any]]
    
    # Metadata
    session_id: str
    thread_id: str
    checkpoint_id: Optional[str]
    created_at: str
    updated_at: str
    metadata: Dict[str, Any]


class NodeStatus(Enum):
    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    SKIPPED = "skipped"


@dataclass
class NodeResult:
    """Resultado de ejecución de un nodo"""
    node_name: str
    status: NodeStatus
    output: Any = None
    error: Optional[str] = None
    metadata: Dict[str, Any] = field(default_factory=dict)
    duration_ms: float = 0.0
    timestamp: str = field(default_factory=lambda: datetime.now().isoformat())


# ============================================================================
# CHECKPOINTER — Persistencia de estado (SQLite)
# ============================================================================

class BaseCheckpointer(ABC):
    """Interfaz base para checkpointers"""
    
    @abstractmethod
    def save(self, thread_id: str, checkpoint_id: str, state: AgentState, metadata: Dict) -> None:
        pass
    
    @abstractmethod
    def load(self, thread_id: str, checkpoint_id: Optional[str] = None) -> Optional[AgentState]:
        pass
    
    @abstractmethod
    def list_checkpoints(self, thread_id: str) -> List[Dict[str, Any]]:
        pass
    
    @abstractmethod
    def delete(self, thread_id: str, checkpoint_id: str) -> None:
        pass


class SQLiteCheckpointer(BaseCheckpointer):
    """Checkpointer persistente en SQLite con soporte para threads y versionado"""
    
    def __init__(self, db_path: str = "~/AIION/data/checkpoints.db"):
        self.db_path = Path(db_path).expanduser()
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        self._lock = threading.RLock()
        self._init_db()
    
    def _init_db(self):
        with self._lock:
            conn = sqlite3.connect(self.db_path)
            conn.execute("""
                CREATE TABLE IF NOT EXISTS checkpoints (
                    thread_id TEXT NOT NULL,
                    checkpoint_id TEXT NOT NULL,
                    parent_checkpoint_id TEXT,
                    state_json TEXT NOT NULL,
                    metadata_json TEXT NOT NULL,
                    created_at TEXT NOT NULL,
                    PRIMARY KEY (thread_id, checkpoint_id)
                )
            """)
            conn.execute("""
                CREATE INDEX IF NOT EXISTS idx_checkpoints_thread 
                ON checkpoints(thread_id, created_at DESC)
            """)
            conn.commit()
            conn.close()
    
    def save(self, thread_id: str, checkpoint_id: str, state: AgentState, metadata: Dict) -> None:
        with self._lock:
            conn = sqlite3.connect(self.db_path)
            conn.execute("""
                INSERT OR REPLACE INTO checkpoints 
                (thread_id, checkpoint_id, parent_checkpoint_id, state_json, metadata_json, created_at)
                VALUES (?, ?, ?, ?, ?, ?)
            """, (
                thread_id,
                checkpoint_id,
                state.get("checkpoint_id"),
                json.dumps(state, ensure_ascii=False),
                json.dumps(metadata, ensure_ascii=False),
                datetime.now().isoformat()
            ))
            conn.commit()
            conn.close()
    
    def load(self, thread_id: str, checkpoint_id: Optional[str] = None) -> Optional[AgentState]:
        with self._lock:
            conn = sqlite3.connect(self.db_path)
            if checkpoint_id:
                row = conn.execute(
                    "SELECT state_json FROM checkpoints WHERE thread_id=? AND checkpoint_id=?",
                    (thread_id, checkpoint_id)
                ).fetchone()
            else:
                row = conn.execute(
                    "SELECT state_json FROM checkpoints WHERE thread_id=? ORDER BY created_at DESC LIMIT 1",
                    (thread_id,)
                ).fetchone()
            conn.close()
            if row:
                return json.loads(row[0])
            return None
    
    def list_checkpoints(self, thread_id: str) -> List[Dict[str, Any]]:
        with self._lock:
            conn = sqlite3.connect(self.db_path)
            rows = conn.execute("""
                SELECT checkpoint_id, parent_checkpoint_id, metadata_json, created_at
                FROM checkpoints WHERE thread_id=? ORDER BY created_at DESC
            """, (thread_id,)).fetchall()
            conn.close()
            return [
                {
                    "checkpoint_id": r[0],
                    "parent_checkpoint_id": r[1],
                    "metadata": json.loads(r[2]),
                    "created_at": r[3]
                }
                for r in rows
            ]
    
    def delete(self, thread_id: str, checkpoint_id: str) -> None:
        with self._lock:
            conn = sqlite3.connect(self.db_path)
            conn.execute(
                "DELETE FROM checkpoints WHERE thread_id=? AND checkpoint_id=?",
                (thread_id, checkpoint_id)
            )
            conn.commit()
            conn.close()


class MemoryCheckpointer(BaseCheckpointer):
    """Checkpointer en memoria para testing/desarrollo"""
    
    def __init__(self):
        self._store: Dict[str, Dict[str, Any]] = {}
        self._lock = threading.RLock()
    
    def save(self, thread_id: str, checkpoint_id: str, state: AgentState, metadata: Dict) -> None:
        with self._lock:
            if thread_id not in self._store:
                self._store[thread_id] = {}
            self._store[thread_id][checkpoint_id] = {
                "state": state,
                "metadata": metadata,
                "created_at": datetime.now().isoformat()
            }
    
    def load(self, thread_id: str, checkpoint_id: Optional[str] = None) -> Optional[AgentState]:
        with self._lock:
            if thread_id not in self._store:
                return None
            if checkpoint_id:
                return self._store[thread_id].get(checkpoint_id, {}).get("state")
            # Latest
            latest = max(self._store[thread_id].items(), key=lambda x: x[1]["created_at"])
            return latest[1]["state"]
    
    def list_checkpoints(self, thread_id: str) -> List[Dict[str, Any]]:
        with self._lock:
            if thread_id not in self._store:
                return []
            return [
                {
                    "checkpoint_id": cid,
                    "parent_checkpoint_id": data["state"].get("checkpoint_id"),
                    "metadata": data["metadata"],
                    "created_at": data["created_at"]
                }
                for cid, data in self._store[thread_id].items()
            ]
    
    def delete(self, thread_id: str, checkpoint_id: str) -> None:
        with self._lock:
            if thread_id in self._store:
                self._store[thread_id].pop(checkpoint_id, None)


# ============================================================================
# STATE GRAPH — Máquina de estados basada en grafo
# ============================================================================

class StateGraph:
    """
    Grafo de estados estilo LangGraph.
    Nodos = funciones que transforman AgentState.
    Edges = transiciones condicionales.
    """
    
    def __init__(self, state_schema: type = AgentState):
        self.state_schema = state_schema
        self.nodes: Dict[str, Callable[[AgentState], AgentState]] = {}
        self.edges: Dict[str, List[str]] = {}  # node -> [next_nodes]
        self.conditional_edges: Dict[str, Callable[[AgentState], str]] = {}
        self.entry_point: Optional[str] = None
        self.finish_point: Optional[str] = None
        self._compiled = False
    
    def add_node(self, name: str, func: Callable[[AgentState], AgentState]) -> "StateGraph":
        """Añade un nodo al grafo"""
        self.nodes[name] = func
        if name not in self.edges:
            self.edges[name] = []
        return self
    
    def add_edge(self, from_node: str, to_node: str) -> "StateGraph":
        """Añade edge incondicional"""
        if from_node not in self.edges:
            self.edges[from_node] = []
        if to_node not in self.edges[from_node]:
            self.edges[from_node].append(to_node)
        return self
    
    def add_conditional_edges(
        self, 
        from_node: str, 
        condition: Callable[[AgentState], str],
        path_map: Optional[Dict[str, str]] = None
    ) -> "StateGraph":
        """Añade edge condicional: condition(state) -> next_node_name"""
        self.conditional_edges[from_node] = condition
        if path_map:
            # Validar que todos los destinos existan
            for dest in path_map.values():
                if dest not in self.nodes and dest != "__end__":
                    raise ValueError(f"Nodo destino '{dest}' no existe")
        return self
    
    def set_entry_point(self, node: str) -> "StateGraph":
        self.entry_point = node
        return self
    
    def set_finish_point(self, node: str) -> "StateGraph":
        self.finish_point = node
        return self
    
    def compile(self, checkpointer: Optional[BaseCheckpointer] = None) -> "CompiledGraph":
        """Compila el grafo para ejecución"""
        if not self.entry_point:
            raise ValueError("Entry point no definido")
        if not self.nodes:
            raise ValueError("Grafo vacío")
        self._compiled = True
        return CompiledGraph(self, checkpointer)
    
    def visualize(self) -> str:
        """Genera representación Mermaid del grafo"""
        lines = ["```mermaid", "graph TD"]
        for node in self.nodes:
            lines.append(f"    {node}[{node}]")
        for from_node, to_nodes in self.edges.items():
            for to_node in to_nodes:
                lines.append(f"    {from_node} --> {to_node}")
        for from_node in self.conditional_edges:
            lines.append(f"    {from_node} -.->|condicional| ...")
        lines.append("```")
        return "\n".join(lines)


class CompiledGraph:
    """Grafo compilado listo para ejecución con checkpoints"""
    
    def __init__(self, graph: StateGraph, checkpointer: Optional[BaseCheckpointer] = None):
        self.graph = graph
        self.checkpointer = checkpointer or MemoryCheckpointer()
        self._interrupt_handlers: Dict[str, Callable] = {}
    
    def invoke(
        self, 
        input_state: AgentState, 
        config: Optional[Dict[str, Any]] = None
    ) -> AgentState:
        """Ejecución síncrona completa"""
        config = config or {}
        thread_id = config.get("thread_id", str(uuid.uuid4()))
        checkpoint_id = config.get("checkpoint_id")
        
        # Cargar checkpoint si existe
        if checkpoint_id:
            saved = self.checkpointer.load(thread_id, checkpoint_id)
            if saved:
                input_state = {**saved, **input_state}  # merge, input tiene prioridad
        
        state = self._ensure_state(input_state)
        state["thread_id"] = thread_id
        state["session_id"] = state.get("session_id", str(uuid.uuid4()))
        
        return self._run(state, config)
    
    def stream(
        self, 
        input_state: AgentState, 
        config: Optional[Dict[str, Any]] = None,
        stream_mode: str = "values"  # "values" | "updates" | "debug"
    ):
        """Streaming de estados intermedios (generador)"""
        config = config or {}
        thread_id = config.get("thread_id", str(uuid.uuid4()))
        checkpoint_id = config.get("checkpoint_id")
        
        if checkpoint_id:
            saved = self.checkpointer.load(thread_id, checkpoint_id)
            if saved:
                input_state = {**saved, **input_state}
        
        state = self._ensure_state(input_state)
        state["thread_id"] = thread_id
        state["session_id"] = state.get("session_id", str(uuid.uuid4()))
        
        yield from self._run_stream(state, config, stream_mode)
    
    def resume(
        self, 
        thread_id: str, 
        checkpoint_id: str, 
        human_input: Any,
        config: Optional[Dict[str, Any]] = None
    ) -> AgentState:
        """Reanuda ejecución desde checkpoint con input humano"""
        config = config or {}
        config["thread_id"] = thread_id
        config["checkpoint_id"] = checkpoint_id
        
        saved = self.checkpointer.load(thread_id, checkpoint_id)
        if not saved:
            raise ValueError(f"Checkpoint {checkpoint_id} no encontrado en thread {thread_id}")
        
        # Inyectar respuesta humana
        saved["interrupt_reason"] = None
        saved["interrupt_data"] = None
        saved["human_response"] = human_input
        saved["status"] = "running"
        
        return self.invoke(saved, config)
    
    def get_state(self, thread_id: str, checkpoint_id: Optional[str] = None) -> Optional[AgentState]:
        """Obtiene estado actual o de checkpoint"""
        return self.checkpointer.load(thread_id, checkpoint_id)
    
    def list_checkpoints(self, thread_id: str) -> List[Dict[str, Any]]:
        return self.checkpointer.list_checkpoints(thread_id)
    
    def _ensure_state(self, state: Dict) -> AgentState:
        """Asegura que el estado tenga todos los campos requeridos"""
        default_state: AgentState = {
            "user_input": "",
            "final_response": "",
            "messages": [],
            "history": [],
            "system_prompt": "",
            "sensor_context": {},
            "memory_context": "",
            "cognitive_context": "",
            "mythos_analysis": {},
            "current_step": 0,
            "max_steps": 10,
            "tool_calls": [],
            "tool_results": [],
            "thoughts": [],
            "status": "running",
            "error": None,
            "interrupt_reason": None,
            "interrupt_data": None,
            "session_id": str(uuid.uuid4()),
            "thread_id": "",
            "checkpoint_id": None,
            "created_at": datetime.now().isoformat(),
            "updated_at": datetime.now().isoformat(),
            "metadata": {},
        }
        default_state.update(state)
        return default_state
    
    def _run(self, state: AgentState, config: Dict) -> AgentState:
        """Ejecución interna del grafo"""
        current_node = self.graph.entry_point
        thread_id = state["thread_id"]
        step = 0
        max_steps = state.get("max_steps", 50)
        
        while current_node and current_node != "__end__" and step < max_steps:
            step += 1
            state["current_step"] = step
            state["updated_at"] = datetime.now().isoformat()
            
            # Checkpoint antes de cada nodo
            checkpoint_id = f"step_{step}_{current_node}_{uuid.uuid4().hex[:8]}"
            state["checkpoint_id"] = checkpoint_id
            self.checkpointer.save(thread_id, checkpoint_id, state, {
                "node": current_node,
                "step": step,
                "status": state["status"]
            })
            
            # Ejecutar nodo
            if current_node not in self.graph.nodes:
                state["status"] = "error"
                state["error"] = f"Nodo '{current_node}' no existe"
                break
            
            try:
                node_func = self.graph.nodes[current_node]
                state = node_func(state)
            except Exception as e:
                state["status"] = "error"
                state["error"] = str(e)
                break
            
            # Verificar interrupción
            if state.get("status") == "awaiting_human":
                # Guardar checkpoint de interrupción
                self.checkpointer.save(thread_id, checkpoint_id, state, {
                    "node": current_node,
                    "step": step,
                    "status": "interrupted",
                    "interrupt_reason": state.get("interrupt_reason")
                })
                return state
            
            # Determinar siguiente nodo
            current_node = self._get_next_node(current_node, state)
        
        if step >= max_steps:
            state["status"] = "error"
            state["error"] = f"Límite de {max_steps} pasos alcanzado"
        
        if state["status"] == "running":
            state["status"] = "completed"
        
        # Checkpoint final
        final_checkpoint = f"final_{uuid.uuid4().hex[:8]}"
        state["checkpoint_id"] = final_checkpoint
        self.checkpointer.save(thread_id, final_checkpoint, state, {
            "node": "END",
            "step": step,
            "status": state["status"]
        })
        
        return state
    
    def _run_stream(self, state: AgentState, config: Dict, stream_mode: str):
        """Ejecución con streaming"""
        current_node = self.graph.entry_point
        thread_id = state["thread_id"]
        step = 0
        max_steps = state.get("max_steps", 50)
        
        while current_node and current_node != "__end__" and step < max_steps:
            step += 1
            state["current_step"] = step
            state["updated_at"] = datetime.now().isoformat()
            
            checkpoint_id = f"step_{step}_{current_node}_{uuid.uuid4().hex[:8]}"
            state["checkpoint_id"] = checkpoint_id
            
            if stream_mode in ("values", "debug"):
                yield {"type": "state", "node": current_node, "state": dict(state), "step": step}
            
            try:
                node_func = self.graph.nodes[current_node]
                prev_state = dict(state)
                state = node_func(state)
                
                if stream_mode == "updates":
                    # Calcular diff
                    yield {"type": "update", "node": current_node, "diff": self._diff(prev_state, state)}
                elif stream_mode == "debug":
                    yield {"type": "node_complete", "node": current_node, "state": dict(state)}
                    
            except Exception as e:
                state["status"] = "error"
                state["error"] = str(e)
                yield {"type": "error", "node": current_node, "error": str(e)}
                break
            
            if state.get("status") == "awaiting_human":
                self.checkpointer.save(thread_id, checkpoint_id, state, {
                    "node": current_node, "step": step, "status": "interrupted"
                })
                yield {"type": "interrupt", "node": current_node, "state": dict(state)}
                return
            
            current_node = self._get_next_node(current_node, state)
        
        if state["status"] == "running":
            state["status"] = "completed"
        
        final_checkpoint = f"final_{uuid.uuid4().hex[:8]}"
        state["checkpoint_id"] = final_checkpoint
        self.checkpointer.save(thread_id, final_checkpoint, state, {"status": state["status"]})
        
        yield {"type": "final", "state": dict(state)}
    
    def _get_next_node(self, current_node: str, state: AgentState) -> Optional[str]:
        """Determina el siguiente nodo basado en edges y conditional edges"""
        # Conditional edge tiene prioridad
        if current_node in self.graph.conditional_edges:
            condition = self.graph.conditional_edges[current_node]
            try:
                next_node = condition(state)
                if next_node == "__end__":
                    return None
                return next_node
            except Exception:
                pass
        
        # Edge incondicional
        edges = self.graph.edges.get(current_node, [])
        if edges:
            return edges[0]  # Primer edge (para branching usar conditional)
        
        # Finish point
        if current_node == self.graph.finish_point:
            return None
        
        return None
    
    def _diff(self, old: Dict, new: Dict) -> Dict:
        """Calcula diferencia entre estados"""
        diff = {}
        all_keys = set(old.keys()) | set(new.keys())
        for k in all_keys:
            if old.get(k) != new.get(k):
                diff[k] = {"old": old.get(k), "new": new.get(k)}
        return diff


# ============================================================================
# NODOS PREDEFINIDOS PARA AIION
# ============================================================================

def create_aiion_nodes(
    build_system_prompt_fn: Callable,
    chat_native_fn: Callable,
    chat_react_text_fn: Callable,
    parse_react_fn: Callable,
    execute_tool_fn: Callable,
    tool_map: Dict,
    tool_call_state: Dict,
    max_iter: int,
    ram_guard: Any,
    sensor_last_fn: Callable,
    memory_load_fn: Callable,
    history_summary_fn: Callable,
    cogindex: Any,
    mythos: Any,
    state_dict: Dict,
    voice_state: Dict,
    speak_fn: Callable,
    notify_fn: Callable,
    history_save_fn: Callable,
) -> Dict[str, Callable[[AgentState], AgentState]]:
    """Factory de nodos específicos para AIION"""
    
    def node_initialize(state: AgentState) -> AgentState:
        """Nodo inicial: prepara contexto, system prompt, etc."""
        user_input = state.get("user_input", "")
        
        # Construir system prompt
        system_prompt = build_system_prompt_fn(user_input)
        
        # Contexto sensorial
        sensor_context = {}
        for s in ["battery", "wifi", "system", "sensors", "location"]:
            d = sensor_last_fn(s)
            if d:
                sensor_context[s] = d
        
        # Memoria e índice cognitivo
        memory_context = memory_load_fn() or ""
        cognitive_context = cogindex.context_block() if hasattr(cogindex, 'context_block') else ""
        
        # Mythos
        mythos_analysis = mythos.analyze(user_input) if user_input else None
        mythos_dict = {}
        if mythos_analysis:
            mythos_dict = {
                "logos": str(mythos_analysis.logos),
                "pathos": str(mythos_analysis.pathos),
                "ethos": str(mythos_analysis.ethos),
                "intent": mythos_analysis.intent,
                "confidence": mythos_analysis.confidence,
                "hint": mythos.build_hint(mythos_analysis),
                "caution": mythos_analysis.caution,
                "metadata": mythos_analysis.metadata
            }
        
        # Historial
        history = state.get("history", [])
        
        return {
            **state,
            "system_prompt": system_prompt,
            "sensor_context": sensor_context,
            "memory_context": memory_context,
            "cognitive_context": cognitive_context,
            "mythos_analysis": mythos_dict,
            "messages": [
                {"role": "system", "content": system_prompt}
            ] + history + [{"role": "user", "content": user_input}],
            "status": "running",
            "current_step": 0,
            "max_steps": state.get("max_steps", max_iter),
        }
    
    def node_llm_native(state: AgentState) -> AgentState:
        """Nodo: LLM con tool calling nativo"""
        if not tool_call_state.get("native", False):
            state["status"] = "error"
            state["error"] = "Modo nativo no disponible"
            return state
        
        messages = state["messages"]
        try:
            kind, data, raw_msg = chat_native_fn(messages)
        except Exception as e:
            state["status"] = "error"
            state["error"] = f"LLM error: {e}"
            return state
        
        if kind == "tool_call":
            # El modelo quiere llamar tools
            tool_calls = raw_msg.get("tool_calls", [])
            state["tool_calls"] = tool_calls
            state["messages"].append({
                "role": "assistant",
                "content": raw_msg.get("content", ""),
                "tool_calls": tool_calls
            })
            state["thoughts"].append(raw_msg.get("content", "").strip())
            return state
        else:
            # Respuesta final
            state["final_response"] = data.strip()
            state["status"] = "completed"
            return state
    
    def node_llm_react(state: AgentState) -> AgentState:
        """Nodo: LLM en modo ReAct (texto plano)"""
        messages = state["messages"]
        try:
            raw = chat_react_text_fn(messages)
        except Exception as e:
            state["status"] = "error"
            state["error"] = f"LLM error: {e}"
            return state
        
        state["messages"].append({"role": "assistant", "content": raw})
        parsed = parse_react_fn(raw)
        
        if parsed[0] == "action":
            _, fn_name, fn_args, thought = parsed
            state["tool_calls"] = [{
                "function": {"name": fn_name, "arguments": fn_args}
            }]
            state["thoughts"].append(thought or "")
            return state
        elif parsed[0] == "final":
            state["final_response"] = parsed[1]
            state["status"] = "completed"
            return state
        
        state["status"] = "error"
        state["error"] = "Respuesta LLM no parseable"
        return state
    
    def node_execute_tools(state: AgentState) -> AgentState:
        """Nodo: Ejecuta tool calls pendientes"""
        tool_calls = state.get("tool_calls", [])
        if not tool_calls:
            return state
        
        results = []
        for tc in tool_calls:
            fn_name = tc.get("function", {}).get("name")
            fn_args = tc.get("function", {}).get("arguments", {})
            call_id = tc.get("id", str(uuid.uuid4()))
            
            if fn_name not in tool_map:
                obs = f"Error: '{fn_name}' no existe. Disponibles: {', '.join(tool_map.keys())}"
            else:
                obs = execute_tool_fn(fn_name, fn_args)
            
            results.append({
                "call_id": call_id,
                "name": fn_name,
                "arguments": fn_args,
                "result": obs
            })
            
            # Añadir al historial de mensajes
            state["messages"].append({
                "role": "tool",
                "content": obs,
                "tool_call_id": call_id,
                "name": fn_name
            })
        
        state["tool_results"] = results
        state["tool_calls"] = []  # Limpiar después de ejecutar
        return state
    
    def node_check_continuation(state: AgentState) -> AgentState:
        """Nodo: Decide si continuar o terminar"""
        if state.get("status") == "completed":
            return state
        if state.get("status") == "error":
            return state
        if state.get("current_step", 0) >= state.get("max_steps", max_iter):
            state["status"] = "error"
            state["error"] = f"Límite de {max_iter} pasos alcanzado"
            return state
        # Continuar
        return state
    
    def node_finalize(state: AgentState) -> AgentState:
        """Nodo final: guarda historial, notifica, TTS"""
        user_input = state.get("user_input", "")
        final_response = state.get("final_response", "")
        
        if final_response:
            history_save_fn(user_input, final_response)
            notify_fn(final_response, steps=state.get("current_step", 0))
            if voice_state.get("enabled"):
                speak_fn(final_response, blocking=False)
        
        state["status"] = "completed"
        return state
    
    def node_human_interrupt(state: AgentState) -> AgentState:
        """Nodo: Interrupción para input humano (ej. confirmación peligrosa)"""
        interrupt_reason = state.get("interrupt_reason", "Se requiere confirmación")
        interrupt_data = state.get("interrupt_data", {})
        
        state["status"] = "awaiting_human"
        state["interrupt_reason"] = interrupt_reason
        state["interrupt_data"] = interrupt_data
        return state
    
    return {
        "initialize": node_initialize,
        "llm_native": node_llm_native,
        "llm_react": node_llm_react,
        "execute_tools": node_execute_tools,
        "check_continuation": node_check_continuation,
        "finalize": node_finalize,
        "human_interrupt": node_human_interrupt,
    }


# ============================================================================
# CONDITIONAL EDGES PARA AIION
# ============================================================================

def route_after_llm(state: AgentState) -> str:
    """Routing después del LLM: tool_call -> execute_tools, final -> finalize"""
    if state.get("tool_calls"):
        # Verificar si alguna tool requiere confirmación (dangerous)
        for tc in state["tool_calls"]:
            fn_name = tc.get("function", {}).get("name", "")
            # Aquí se podría integrar con DANGEROUS_TOOLS
            if fn_name in ("run_shell_command", "write_file", "replace", "enviar_sms", "hacer_llamada"):
                return "human_interrupt"
        return "execute_tools"
    elif state.get("final_response"):
        return "finalize"
    elif state.get("status") == "error":
        return "finalize"
    return "check_continuation"


def route_after_tools(state: AgentState) -> str:
    """Routing después de ejecutar tools: siempre vuelve al LLM"""
    if state.get("status") == "error":
        return "finalize"
    return "llm_native"  # o llm_react según modo


def route_after_interrupt(state: AgentState) -> str:
    """Routing después de interrupción humana"""
    # La reanudación viene via resume(), este nodo solo marca el estado
    return "check_continuation"


def route_continuation(state: AgentState) -> str:
    """Routing de continuación: LLM o finalize"""
    if state.get("status") == "completed":
        return "finalize"
    if state.get("status") == "error":
        return "finalize"
    # Decidir modo LLM
    if state.get("metadata", {}).get("tool_mode") == "react":
        return "llm_react"
    return "llm_native"


# ============================================================================
# GRAPH BUILDER PARA AIION
# ============================================================================

def build_aiion_graph(
    build_system_prompt_fn: Callable,
    chat_native_fn: Callable,
    chat_react_text_fn: Callable,
    parse_react_fn: Callable,
    execute_tool_fn: Callable,
    tool_map: Dict,
    tool_call_state: Dict,
    max_iter: int,
    ram_guard: Any,
    sensor_last_fn: Callable,
    memory_load_fn: Callable,
    history_summary_fn: Callable,
    cogindex: Any,
    mythos: Any,
    state_dict: Dict,
    voice_state: Dict,
    speak_fn: Callable,
    notify_fn: Callable,
    history_save_fn: Callable,
    checkpointer: Optional[BaseCheckpointer] = None,
) -> CompiledGraph:
    """Construye y compila el grafo completo de AIION"""
    
    nodes = create_aiion_nodes(
        build_system_prompt_fn=build_system_prompt_fn,
        chat_native_fn=chat_native_fn,
        chat_react_text_fn=chat_react_text_fn,
        parse_react_fn=parse_react_fn,
        execute_tool_fn=execute_tool_fn,
        tool_map=tool_map,
        tool_call_state=tool_call_state,
        max_iter=max_iter,
        ram_guard=ram_guard,
        sensor_last_fn=sensor_last_fn,
        memory_load_fn=memory_load_fn,
        history_summary_fn=history_summary_fn,
        cogindex=cogindex,
        mythos=mythos,
        state_dict=state_dict,
        voice_state=voice_state,
        speak_fn=speak_fn,
        notify_fn=notify_fn,
        history_save_fn=history_save_fn,
    )
    
    graph = StateGraph(AgentState)
    
    # Añadir nodos
    for name, func in nodes.items():
        graph.add_node(name, func)
    
    # Edges
    graph.set_entry_point("initialize")
    graph.add_edge("initialize", "llm_native")  # conditional edge maneja react
    
    # Conditional edges
    graph.add_conditional_edges("llm_native", route_after_llm)
    graph.add_conditional_edges("llm_react", route_after_llm)
    graph.add_conditional_edges("execute_tools", route_after_tools)
    graph.add_conditional_edges("human_interrupt", route_after_interrupt)
    graph.add_conditional_edges("check_continuation", route_continuation)
    
    graph.set_finish_point("finalize")
    
    return graph.compile(checkpointer)


# ============================================================================
# HELPERS PARA INTEGRACIÓN EN CORE.PY
# ============================================================================

def create_initial_state(
    user_input: str,
    history: List[Dict],
    session_id: Optional[str] = None,
    thread_id: Optional[str] = None,
    max_steps: int = 10,
    metadata: Optional[Dict] = None
) -> AgentState:
    """Crea estado inicial para el grafo"""
    return {
        "user_input": user_input,
        "final_response": "",
        "messages": [],
        "history": history[-20:] if history else [],
        "system_prompt": "",
        "sensor_context": {},
        "memory_context": "",
        "cognitive_context": "",
        "mythos_analysis": {},
        "current_step": 0,
        "max_steps": max_steps,
        "tool_calls": [],
        "tool_results": [],
        "thoughts": [],
        "status": "running",
        "error": None,
        "interrupt_reason": None,
        "interrupt_data": None,
        "session_id": session_id or str(uuid.uuid4()),
        "thread_id": thread_id or str(uuid.uuid4()),
        "checkpoint_id": None,
        "created_at": datetime.now().isoformat(),
        "updated_at": datetime.now().isoformat(),
        "metadata": metadata or {},
    }


def run_graph_sync(
    graph: CompiledGraph,
    user_input: str,
    history: List[Dict],
    thread_id: Optional[str] = None,
    max_steps: int = 10,
) -> AgentState:
    """Ejecuta grafo sincrónicamente y retorna estado final"""
    initial_state = create_initial_state(
        user_input=user_input,
        history=history,
        thread_id=thread_id,
        max_steps=max_steps,
    )
    return graph.invoke(initial_state, config={"thread_id": thread_id or initial_state["thread_id"]})


def run_graph_stream(
    graph: CompiledGraph,
    user_input: str,
    history: List[Dict],
    thread_id: Optional[str] = None,
    max_steps: int = 10,
    stream_mode: str = "values"
):
    """Ejecuta grafo con streaming"""
    initial_state = create_initial_state(
        user_input=user_input,
        history=history,
        thread_id=thread_id,
        max_steps=max_steps,
    )
    return graph.stream(initial_state, config={"thread_id": thread_id or initial_state["thread_id"]}, stream_mode=stream_mode)


# ============================================================================
# EXPORTS
# ============================================================================

__all__ = [
    # Types
    "AgentState",
    "NodeStatus",
    "NodeResult",
    # Checkpointers
    "BaseCheckpointer",
    "SQLiteCheckpointer",
    "MemoryCheckpointer",
    # Graph
    "StateGraph",
    "CompiledGraph",
    # Nodes & Routing
    "create_aiion_nodes",
    "route_after_llm",
    "route_after_tools",
    "route_after_interrupt",
    "route_continuation",
    # Builder
    "build_aiion_graph",
    # Helpers
    "create_initial_state",
    "run_graph_sync",
    "run_graph_stream",
]