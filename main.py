import asyncio
import json
import os
from typing import Any, Dict, List, Optional
from mcp.server.fastmcp import FastMCP
from pyzotero import zotero

# Zotero配置 - 可以通过环境变量或工具设置
ZOTERO_LIBRARY_ID = os.getenv("ZOTERO_LIBRARY_ID", "")
ZOTERO_API_KEY = os.getenv("ZOTERO_API_KEY", "")
ZOTERO_LIBRARY_TYPE = os.getenv("ZOTERO_LIBRARY_TYPE", "user")  # 或 'group'

# 创建FastMCP应用实例
app = FastMCP("zotero-controller")

# 全局Zotero客户端变量
zot = None

def get_zotero_client():
    """获取Zotero客户端，如果未配置则返回None"""
    global zot
    if not ZOTERO_LIBRARY_ID or not ZOTERO_API_KEY:
        return None
    if zot is None:
        try:
            zot = zotero.Zotero(ZOTERO_LIBRARY_ID, ZOTERO_LIBRARY_TYPE, ZOTERO_API_KEY)
        except Exception as e:
            return None
    return zot

@app.tool()
def configure_zotero(library_id: str, api_key: str, library_type: str = "user") -> str:
    """配置Zotero API 凭据"""
    global ZOTERO_LIBRARY_ID, ZOTERO_API_KEY, ZOTERO_LIBRARY_TYPE, zot
    
    # 验证输入
    if not library_id or not api_key:
        return "错误：库ID和API密钥不能为空"
    
    if library_type not in ["user", "group"]:
        return "错误：库类型必须是 'user' 或 'group'"
    
    # 更新配置
    ZOTERO_LIBRARY_ID = library_id.strip()
    ZOTERO_API_KEY = api_key.strip()
    ZOTERO_LIBRARY_TYPE = library_type.strip()
    
    # 重置客户端
    zot = None
    
    # 测试连接
    try:
        test_client = zotero.Zotero(ZOTERO_LIBRARY_ID, ZOTERO_LIBRARY_TYPE, ZOTERO_API_KEY)
        # 尝试获取一个条目来验证配置
        test_client.top(limit=1)
        return f"✅ Zotero配置成功！\n库ID: {ZOTERO_LIBRARY_ID}\n库类型: {ZOTERO_LIBRARY_TYPE}"
    except Exception as e:
        return f"❌ Zotero配置失败: {str(e)}\n请检查您的库ID和API密钥是否正确"

@app.tool()
def list_items(limit: int = 50) -> str:
    """获取Zotero库中的所有条目"""
    zot = get_zotero_client()
    if zot is None:
        return "❌ 错误：Zotero未配置。请先使用 configure_zotero 工具设置您的API凭据。"
    
    try:
        items = zot.top(limit=limit)
        result = []
        for item in items:
            result.append({
                "key": item.get("key"),
                "title": item.get("data", {}).get("title", "无标题"),
                "itemType": item.get("data", {}).get("itemType"),
                "dateAdded": item.get("data", {}).get("dateAdded")
            })
        return f"找到 {len(result)} 个条目:\n" + json.dumps(result, indent=2, ensure_ascii=False)
    except Exception as e:
        return f"获取条目列表失败: {str(e)}"

@app.tool()
def delete_item(item_key: str) -> str:
    """删除指定的Zotero条目"""
    zot = get_zotero_client()
    if zot is None:
        return "❌ 错误：Zotero未配置。请先使用 configure_zotero 工具设置您的API凭据。"
    
    try:
        zot.delete_item(item_key)
        return f"成功删除条目: {item_key}"
    except Exception as e:
        return f"删除条目失败: {str(e)}"

@app.tool()
def delete_items_batch(item_keys: List[str]) -> str:
    """批量删除多个Zotero条目"""
    zot = get_zotero_client()
    if zot is None:
        return "❌ 错误：Zotero未配置。请先使用 configure_zotero 工具设置您的API凭据。"
    
    try:
        success_count = 0
        errors = []
        for key in item_keys:
            try:
                zot.delete_item(key)
                success_count += 1
            except Exception as e:
                errors.append(f"{key}: {str(e)}")
        
        result = f"成功删除 {success_count} 个条目"
        if errors:
            result += f"\n删除失败的条目:\n" + "\n".join(errors)
        
        return result
    except Exception as e:
        return f"批量删除失败: {str(e)}"

@app.tool()
def search_items(query: str, item_type: Optional[str] = None) -> str:
    """搜索Zotero条目"""
    zot = get_zotero_client()
    if zot is None:
        return "❌ 错误：Zotero未配置。请先使用 configure_zotero 工具设置您的API凭据。"
    
    try:
        items = zot.everything(zot.top())
        filtered_items = []
        
        for item in items:
            data = item.get("data", {})
            title = data.get("title", "").lower()
            
            # 基本搜索匹配
            if query.lower() in title:
                if item_type is None or data.get("itemType") == item_type:
                    filtered_items.append({
                        "key": item.get("key"),
                        "title": data.get("title", "无标题"),
                        "itemType": data.get("itemType"),
                        "dateAdded": data.get("dateAdded")
                    })
        
        return f"搜索结果 ({len(filtered_items)} 个条目):\n" + json.dumps(filtered_items, indent=2, ensure_ascii=False)
    except Exception as e:
        return f"搜索失败: {str(e)}"

@app.tool()
def get_item_details(item_key: str) -> str:
    """获取指定条目的详细信息"""
    zot = get_zotero_client()
    if zot is None:
        return "❌ 错误：Zotero未配置。请先使用 configure_zotero 工具设置您的API凭据。"
    
    try:
        item = zot.item(item_key)
        return f"条目详情:\n" + json.dumps(item, indent=2, ensure_ascii=False)
    except Exception as e:
        return f"获取条目详情失败: {str(e)}"

@app.tool()
def retain_items_by_criteria(
    criteria: Dict[str, Any], 
    dry_run: bool = True
) -> str:
    """根据条件保留特定条目，删除其他条目"""
    zot = get_zotero_client()
    if zot is None:
        return "❌ 错误：Zotero未配置。请先使用 configure_zotero 工具设置您的API凭据。"
    
    try:
        all_items = zot.everything(zot.top())
        items_to_retain = []
        items_to_delete = []
        
        for item in all_items:
            data = item.get("data", {})
            should_retain = True
            
            # 检查各种条件
            if "item_type" in criteria:
                if data.get("itemType") != criteria["item_type"]:
                    should_retain = False
            
            if "title_contains" in criteria:
                if criteria["title_contains"].lower() not in data.get("title", "").lower():
                    should_retain = False
            
            # 可以添加更多条件检查...
            
            if should_retain:
                items_to_retain.append(item)
            else:
                items_to_delete.append(item)
        
        result = f"根据条件筛选结果:\n"
        result += f"保留条目: {len(items_to_retain)} 个\n"
        result += f"待删除条目: {len(items_to_delete)} 个\n"
        
        if dry_run:
            result += "\n[预览模式] 待删除的条目:\n"
            for item in items_to_delete[:10]:  # 只显示前10个
                data = item.get("data", {})
                result += f"- {data.get('title', '无标题')} ({item.get('key')})\n"
            if len(items_to_delete) > 10:
                result += f"... 还有 {len(items_to_delete) - 10} 个条目\n"
        else:
            # 实际删除
            deleted_count = 0
            for item in items_to_delete:
                try:
                    zot.delete_item(item.get("key"))
                    deleted_count += 1
                except Exception as e:
                    result += f"删除失败 {item.get('key')}: {str(e)}\n"
            result += f"\n实际删除了 {deleted_count} 个条目"
        
        return result
    except Exception as e:
        return f"执行筛选操作失败: {str(e)}"

# 添加资源
@app.resource("zotero://library/stats")
def get_library_stats() -> str:
    """获取Zotero库的统计信息"""
    zot = get_zotero_client()
    if zot is None:
        return json.dumps({"error": "Zotero未配置。请先使用 configure_zotero 工具设置您的API凭据。"}, ensure_ascii=False)
    
    try:
        items = zot.top()
        total_count = len(items)
        
        # 统计不同类型的条目
        type_counts = {}
        for item in items:
            item_type = item.get("data", {}).get("itemType", "unknown")
            type_counts[item_type] = type_counts.get(item_type, 0) + 1
        
        stats = {
            "total_items": total_count,
            "item_types": type_counts
        }
        
        return json.dumps(stats, indent=2, ensure_ascii=False)
    except Exception as e:
        return json.dumps({"error": f"获取库统计信息失败: {str(e)}"}, ensure_ascii=False)

@app.resource("zotero://library/recent")
def get_recent_items() -> str:
    """获取最近添加的条目"""
    zot = get_zotero_client()
    if zot is None:
        return json.dumps({"error": "Zotero未配置。请先使用 configure_zotero 工具设置您的API凭据。"}, ensure_ascii=False)
    
    try:
        items = zot.top(limit=10)
        recent_items = []
        
        for item in items:
            data = item.get("data", {})
            recent_items.append({
                "key": item.get("key"),
                "title": data.get("title", "无标题"),
                "itemType": data.get("itemType"),
                "dateAdded": data.get("dateAdded")
            })
        
        return json.dumps(recent_items, indent=2, ensure_ascii=False)
    except Exception as e:
        return json.dumps({"error": f"获取最近条目失败: {str(e)}"}, ensure_ascii=False)

@app.tool()
def check_zotero_config() -> str:
    """检查当前Zotero配置状态"""
    if not ZOTERO_LIBRARY_ID or not ZOTERO_API_KEY:
        return "❌ Zotero未配置\n请使用 configure_zotero 工具设置您的API凭据\n\n需要的信息:\n- library_id: 您的Zotero库ID\n- api_key: 您的Zotero API密钥\n- library_type: 'user' 或 'group'"
    
    # 隐藏API密钥的部分内容
    masked_key = ZOTERO_API_KEY[:8] + "*" * (len(ZOTERO_API_KEY) - 8) if len(ZOTERO_API_KEY) > 8 else "*" * len(ZOTERO_API_KEY)
    
    return f"✅ Zotero已配置\n库ID: {ZOTERO_LIBRARY_ID}\n库类型: {ZOTERO_LIBRARY_TYPE}\nAPI密钥: {masked_key}"

# 启动MCP服务器
if __name__ == "__main__":
    app.run(transport='stdio')  # 使用标准输入输出作为传输方式