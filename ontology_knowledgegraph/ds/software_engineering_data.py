"""软件工程本体演示 - 基于SQLite数据库的面向对象实现"""
import sqlite3
import os
from typing import List, Dict, Any
from .data_source_mapper import DataSourceMapper

class SoftwareEngineeringDemo:
    """软件工程本体演示"""
    
    def __init__(self, db_path: str = "software_engineering.db"):
        self.db_path = db_path
        self.mapper = DataSourceMapper()
    
    def create_database(self) -> bool:
        """创建软件工程演示数据库"""
        try:
            # 删除现有数据库
            if os.path.exists(self.db_path):
                os.remove(self.db_path)
            
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            # 创建项目表
            cursor.execute("""
                CREATE TABLE projects (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    name TEXT NOT NULL,
                    description TEXT,
                    status TEXT DEFAULT 'active',
                    start_date DATE,
                    end_date DATE,
                    budget REAL,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            """)
            
            # 创建团队表
            cursor.execute("""
                CREATE TABLE teams (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    name TEXT NOT NULL,
                    project_id INTEGER,
                    leader_id INTEGER,
                    description TEXT,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    FOREIGN KEY (project_id) REFERENCES projects(id)
                )
            """)
            
            # 创建开发者表
            cursor.execute("""
                CREATE TABLE developers (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    name TEXT NOT NULL,
                    email TEXT UNIQUE,
                    role TEXT DEFAULT 'developer',
                    team_id INTEGER,
                    experience_years INTEGER DEFAULT 0,
                    skills TEXT,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    FOREIGN KEY (team_id) REFERENCES teams(id)
                )
            """)
            
            # 创建需求表
            cursor.execute("""
                CREATE TABLE requirements (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    title TEXT NOT NULL,
                    description TEXT,
                    project_id INTEGER,
                    priority TEXT DEFAULT 'medium',
                    status TEXT DEFAULT 'open',
                    complexity TEXT DEFAULT 'medium',
                    assigned_to INTEGER,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    FOREIGN KEY (project_id) REFERENCES projects(id),
                    FOREIGN KEY (assigned_to) REFERENCES developers(id)
                )
            """)
            
            # 创建任务表
            cursor.execute("""
                CREATE TABLE tasks (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    title TEXT NOT NULL,
                    description TEXT,
                    requirement_id INTEGER,
                    assigned_to INTEGER,
                    status TEXT DEFAULT 'todo',
                    priority TEXT DEFAULT 'medium',
                    estimated_hours REAL,
                    actual_hours REAL,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    FOREIGN KEY (requirement_id) REFERENCES requirements(id),
                    FOREIGN KEY (assigned_to) REFERENCES developers(id)
                )
            """)
            
            # 插入示例数据
            self._insert_sample_data(cursor)
            
            conn.commit()
            conn.close()
            
            print(f"数据库 {self.db_path} 创建成功")
            return True
            
        except Exception as e:
            print(f"创建数据库失败: {e}")
            return False
    
    def _insert_sample_data(self, cursor):
        """插入示例数据"""
        # 插入项目
        projects_data = [
            ("电商平台项目", "在线购物和交易的综合平台", "active", "2024-01-01", "2024-12-31", 500000.0),
            ("移动应用项目", "跨平台移动应用程序", "planning", "2024-03-01", "2024-10-31", 300000.0),
            ("数据分析平台", "企业级数据分析工具", "completed", "2023-06-01", "2023-12-31", 200000.0)
        ]
        
        cursor.executemany("""
            INSERT INTO projects (name, description, status, start_date, end_date, budget)
            VALUES (?, ?, ?, ?, ?, ?)
        """, projects_data)
        
        # 插入团队
        teams_data = [
            ("前端开发团队", 1, 1, "负责用户界面开发"),
            ("后端开发团队", 1, 2, "负责服务器端开发"),
            ("移动开发团队", 2, 3, "负责移动应用开发"),
            ("数据团队", 3, 4, "负责数据处理和分析")
        ]
        
        cursor.executemany("""
            INSERT INTO teams (name, project_id, leader_id, description)
            VALUES (?, ?, ?, ?)
        """, teams_data)
        
        # 插入开发者
        developers_data = [
            ("张三", "zhangsan@company.com", "frontend_developer", 1, 3, "React,Vue,JavaScript"),
            ("李四", "lisi@company.com", "backend_developer", 2, 5, "Python,Java,Spring"),
            ("王五", "wangwu@company.com", "mobile_developer", 3, 4, "React Native,Flutter"),
            ("赵六", "zhaoliu@company.com", "data_scientist", 4, 6, "Python,R,SQL"),
            ("钱七", "qianqi@company.com", "fullstack_developer", 1, 4, "Node.js,React,Python"),
            ("孙八", "sunba@company.com", "devops_engineer", 2, 3, "Docker,Kubernetes,AWS")
        ]
        
        cursor.executemany("""
            INSERT INTO developers (name, email, role, team_id, experience_years, skills)
            VALUES (?, ?, ?, ?, ?, ?)
        """, developers_data)
        
        # 插入需求
        requirements_data = [
            ("用户注册功能", "用户可以通过邮箱或手机号注册账户", 1, "high", "open", "medium", 1),
            ("商品浏览功能", "用户可以浏览和搜索商品", 1, "high", "in_progress", "medium", 2),
            ("购物车功能", "用户可以添加商品到购物车", 1, "medium", "open", "low", 1),
            ("订单管理功能", "用户可以查看和管理订单", 1, "medium", "open", "high", 2),
            ("移动端适配", "适配移动设备界面", 2, "high", "planning", "medium", 3),
            ("数据分析仪表板", "提供数据可视化界面", 3, "medium", "completed", "high", 4)
        ]
        
        cursor.executemany("""
            INSERT INTO requirements (title, description, project_id, priority, status, complexity, assigned_to)
            VALUES (?, ?, ?, ?, ?, ?, ?)
        """, requirements_data)
        
        # 插入任务
        tasks_data = [
            ("设计注册页面", "设计用户注册界面", 1, 1, "todo", "high", 8.0, None),
            ("实现注册API", "开发用户注册后端接口", 1, 2, "in_progress", "high", 12.0, 6.0),
            ("商品列表页面", "开发商品展示页面", 2, 1, "todo", "medium", 16.0, None),
            ("搜索功能实现", "实现商品搜索功能", 2, 2, "todo", "medium", 10.0, None),
            ("购物车UI设计", "设计购物车界面", 3, 1, "todo", "medium", 6.0, None),
            ("移动端导航", "实现移动端导航组件", 5, 3, "planning", "medium", 8.0, None),
            ("数据图表组件", "开发数据可视化组件", 6, 4, "completed", "high", 20.0, 18.0)
        ]
        
        cursor.executemany("""
            INSERT INTO tasks (title, description, requirement_id, assigned_to, status, priority, estimated_hours, actual_hours)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
        """, tasks_data)
    
    def build_ontology_from_database(self) -> Dict[str, Any]:
        """从数据库构建本体"""
        table_names = ["projects", "teams", "developers", "requirements", "tasks"]
        return self.mapper.build_ontology_from_database(self.db_path, table_names)
    
    
    def get_database_statistics(self) -> Dict[str, Any]:
        """获取数据库统计信息"""
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            stats = {}
            
            # 统计各表的记录数
            tables = ["projects", "teams", "developers", "requirements", "tasks"]
            for table in tables:
                cursor.execute(f"SELECT COUNT(*) FROM {table}")
                count = cursor.fetchone()[0]
                stats[f"{table}_count"] = count
            
            # 统计项目状态分布
            cursor.execute("SELECT status, COUNT(*) FROM projects GROUP BY status")
            project_status = dict(cursor.fetchall())
            stats["project_status_distribution"] = project_status
            
            # 统计任务状态分布
            cursor.execute("SELECT status, COUNT(*) FROM tasks GROUP BY status")
            task_status = dict(cursor.fetchall())
            stats["task_status_distribution"] = task_status
            
            # 统计开发者技能分布
            cursor.execute("SELECT role, COUNT(*) FROM developers GROUP BY role")
            developer_roles = dict(cursor.fetchall())
            stats["developer_role_distribution"] = developer_roles
            
            conn.close()
            return stats
            
        except Exception as e:
            print(f"获取数据库统计失败: {e}")
            return {"error": str(e)}
    
    def demonstrate_relations(self) -> List[Dict[str, Any]]:
        """演示关系分析"""
        ontology_data = self.build_ontology_from_database()
        instances = ontology_data.get("instances", [])
        
        relations_demo = []
        
        for instance in instances:
            for relation in instance.relations:
                relation_info = {
                    "subject": instance.name,
                    "relation_type": relation.get("type"),
                    "relation_name": relation.get("relation_name"),
                    "object": relation.get("object"),
                    "confidence": relation.get("confidence")
                }
                relations_demo.append(relation_info)
        
        return relations_demo

def main():
    """主函数 - 演示软件工程本体"""
    demo = SoftwareEngineeringDemo()
    
    print("开始构建基于数据库的软件工程本体演示...")
    
    # 1. 创建数据库
    if not demo.create_database():
        print("数据库创建失败")
        return
    
    # 2. 获取数据库统计
    stats = demo.get_database_statistics()
    print("\n数据库统计信息:")
    for key, value in stats.items():
        if not key.endswith("_distribution"):
            print(f"  {key}: {value}")
    
    # 3. 构建本体
    ontology_data = demo.build_ontology_from_database()
    if "error" in ontology_data:
        print(f"构建本体失败: {ontology_data['error']}")
        return
    
    print(f"\n基于数据库的本体构建成功:")
    print(f"  - 类数量: {len(ontology_data['classes'])}")
    print(f"  - 实例数量: {len(ontology_data['instances'])}")
    print(f"  - 数据源数量: {len(ontology_data['data_sources'])}")
    
    # 4. 演示关系分析
    relations = demo.demonstrate_relations()
    print(f"\n发现的关系数量: {len(relations)}")
    
    # 显示前5个关系
    print("\n关系示例:")
    for i, relation in enumerate(relations[:5]):
        print(f"  {i+1}. {relation['subject']} --[{relation['relation_name']}]--> {relation['object']}")
    
    print("\n基于数据库的软件工程本体演示完成！")

if __name__ == "__main__":
    main()
