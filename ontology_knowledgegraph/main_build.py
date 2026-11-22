"""面向对象知识图谱构建程序 - 基于直接Neo4j实现"""
import logging
import sys
import sqlite3
from typing import Optional, Dict, List, Any
from datetime import datetime

from config.config import NEO4J_URI, NEO4J_USER, NEO4J_PASSWORD
from config.neo4j_connector import Neo4jConnector
from ontology.ontology_models import (
    OntologyClass, OntologyInstance, SemanticRelation, 
    RelationType, PropertyDefinition, MethodDefinition
)
from ds.software_engineering_data import SoftwareEngineeringDemo
from ontology.ontology_models import DataSourceType
from ds.data_source_mapper import DataSourceMapper
from ontology.ontology_builder import DirectNeo4jOntologyBuilder

# 配置日志
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

class SoftwareEngineeringEntityBuilder:
    """软件工程实体构建器 - 集成到主构建程序中"""
    
    @staticmethod 
    def create_developer_class(data_source: Optional[Any] = None) -> OntologyClass:
        """创建开发者实体类"""
        properties = [
            PropertyDefinition(
                name="id",
                domain="Developer",
                range_type="integer",
                is_required=True,
                is_unique=True,
                validation_rules=["positive_integer"]
            ),
            PropertyDefinition(
                name="name",
                domain="Developer",
                range_type="string",
                is_required=True,
                validation_rules=["non_empty_string", "max_length_100"]
            ),
            PropertyDefinition(
                name="email",
                domain="Developer",
                range_type="string",
                is_required=True,
                is_unique=True,
                validation_rules=["email_format"]
            ),
            PropertyDefinition(
                name="role",
                domain="Developer",
                range_type="string",
                is_required=False,
                default_value="developer"
            ),
            PropertyDefinition(
                name="experience_years",
                domain="Developer",
                range_type="integer",
                is_required=False,
                validation_rules=["non_negative_integer"]
            ),
            PropertyDefinition(
                name="team_id",
                domain="Developer",
                range_type="integer",
                is_required=False
            ),
            PropertyDefinition(
                name="created_at",
                domain="Developer",
                range_type="datetime",
                is_required=True
            )
        ]
        
        methods = [
            MethodDefinition(
                name="assign_to_team",
                parameters=[{"name": "team_id", "type": "integer"}],
                return_type="boolean",
                description="将开发者分配到团队",
                implementation="self.team_id = team_id; return True"
            ),
            MethodDefinition(
                name="get_team_members",
                parameters=[],
                return_type="List[Developer]",
                description="获取同团队的其他开发者"
            ),
            MethodDefinition(
                name="calculate_experience_level",
                parameters=[],
                return_type="string",
                description="根据经验年数计算技能等级"
            )
        ]
        
        return OntologyClass(
            name="Developer",
            label="开发者",
            definition="软件工程中的开发者实体，代表参与项目开发的人员",
            namespace="software_engineering",
            properties=properties,
            methods=methods,
            data_source=data_source,
            class_variables={
                "DEFAULT_ROLE": "developer",
                "MAX_EXPERIENCE_YEARS": 50
            },
            constraints=[
                "email必须唯一",
                "experience_years必须非负",
                "name不能为空"
            ]
        )
    
    @staticmethod
    def create_project_class(data_source: Optional[Any] = None) -> OntologyClass:
        """创建项目实体类"""
        properties = [
            PropertyDefinition(
                name="id",
                domain="Project",
                range_type="integer",
                is_required=True,
                is_unique=True
            ),
            PropertyDefinition(
                name="name",
                domain="Project",
                range_type="string",
                is_required=True,
                validation_rules=["non_empty_string"]
            ),
            PropertyDefinition(
                name="description",
                domain="Project",
                range_type="string",
                is_required=False
            ),
            PropertyDefinition(
                name="status",
                domain="Project",
                range_type="string",
                is_required=True,
                default_value="planning",
                validation_rules=["valid_status"]
            ),
            PropertyDefinition(
                name="start_date",
                domain="Project",
                range_type="datetime",
                is_required=True
            ),
            PropertyDefinition(
                name="end_date",
                domain="Project",
                range_type="datetime",
                is_required=False
            ),
            PropertyDefinition(
                name="created_at",
                domain="Project",
                range_type="datetime",
                is_required=True
            )
        ]
        
        methods = [
            MethodDefinition(
                name="add_team",
                parameters=[{"name": "team", "type": "Team"}],
                return_type="boolean",
                description="添加团队到项目"
            ),
            MethodDefinition(
                name="get_all_teams",
                parameters=[],
                return_type="List[Team]",
                description="获取项目的所有团队"
            ),
            MethodDefinition(
                name="calculate_progress",
                parameters=[],
                return_type="float",
                description="计算项目进度百分比"
            )
        ]
        
        return OntologyClass(
            name="Project",
            label="项目",
            definition="软件工程项目实体，代表一个完整的软件开发项目",
            namespace="software_engineering",
            properties=properties,
            methods=methods,
            data_source=data_source,
            class_variables={
                "VALID_STATUSES": ["planning", "active", "on_hold", "completed", "cancelled"],
                "DEFAULT_STATUS": "planning"
            }
        )
    
    @classmethod
    def create_all_entities(cls, data_sources: Dict[str, Any]) -> Dict[str, OntologyClass]:
        """创建所有软件工程实体类"""
        entities = {}
        
        # 创建各个实体类
        entities["Developer"] = cls.create_developer_class(
            data_sources.get("developers")
        )
        entities["Project"] = cls.create_project_class(
            data_sources.get("projects")
        )
        
        return entities

class TableToEntityMapper:
    """表结构到实体模型的映射器 - 集成到主构建程序中"""
    
    def __init__(self, db_path: str):
        self.db_path = db_path
        self.conn = None
    
    def connect(self) -> bool:
        """连接到数据库"""
        try:
            self.conn = sqlite3.connect(self.db_path)
            return True
        except Exception as e:
            logger.error(f"数据库连接失败: {e}")
            return False
    
    def close(self):
        """关闭数据库连接"""
        if self.conn:
            self.conn.close()
    
    def get_table_schema(self, table_name: str) -> Dict[str, Any]:
        """获取表结构信息"""
        if not self.conn:
            return {}
        
        cursor = self.conn.cursor()
        
        # 获取列信息
        cursor.execute(f"PRAGMA table_info({table_name})")
        columns = cursor.fetchall()
        
        schema = {
            "table_name": table_name,
            "columns": []
        }
        
        # 处理列信息
        for col in columns:
            column_info = {
                "name": col[1],
                "type": col[2],
                "not_null": bool(col[3]),
                "default_value": col[4],
                "primary_key": bool(col[5])
            }
            schema["columns"].append(column_info)
        
        return schema
    
    def generate_entity_from_table(self, table_name: str) -> OntologyClass:
        """从表生成实体类"""
        schema = self.get_table_schema(table_name)
        
        # 生成属性
        properties = []
        for column in schema["columns"]:
            # 映射SQLite类型到Python类型
            type_mapping = {
                "INTEGER": "integer",
                "TEXT": "string",
                "VARCHAR": "string",
                "REAL": "decimal",
                "BOOLEAN": "boolean",
                "DATETIME": "datetime"
            }
            
            python_type = type_mapping.get(column["type"].upper(), "string")
            
            prop = PropertyDefinition(
                name=column["name"],
                domain=table_name,
                range_type=python_type,
                is_required=column["not_null"],
                is_unique=column["primary_key"],
                default_value=column["default_value"]
            )
            properties.append(prop)
        
        # 创建数据源
        from ontology.ontology_models import SQLiteDataSource
        data_source = SQLiteDataSource(
            name=f"{table_name}_source",
            connection_string=self.db_path,
            table_name=table_name
        )
        
        # 创建实体类
        entity_class = OntologyClass(
            name=table_name,
            label=table_name,
            definition=f"从数据库表 {table_name} 生成的面向对象实体类",
            namespace="database_generated",
            properties=properties,
            data_source=data_source
        )
        
        return entity_class
    
    def generate_all_entities(self) -> Dict[str, OntologyClass]:
        """生成所有表的实体类"""
        if not self.connect():
            return {}
        
        try:
            # 获取所有表名
            cursor = self.conn.cursor()
            cursor.execute("SELECT name FROM sqlite_master WHERE type='table'")
            tables = [row[0] for row in cursor.fetchall()]
            
            entities = {}
            for table_name in tables:
                entity = self.generate_entity_from_table(table_name)
                entities[table_name] = entity
                logger.info(f"生成实体类: {table_name}")
            
            return entities
            
        except Exception as e:
            logger.error(f"生成实体类失败: {e}")
            return {}
        finally:
            self.close()

class EntityInstanceManager:
    """实体实例管理器 - 集成到主构建程序中"""
    
    def __init__(self, db_path: str):
        self.db_path = db_path
        self.conn = None
        self.entity_classes: Dict[str, OntologyClass] = {}
        self.instances: Dict[str, List[OntologyInstance]] = {}
        self.table_mapper = TableToEntityMapper(db_path)
    
    def connect(self) -> bool:
        """连接到数据库"""
        try:
            self.conn = sqlite3.connect(self.db_path)
            return True
        except Exception as e:
            logger.error(f"数据库连接失败: {e}")
            return False
    
    def close(self):
        """关闭数据库连接"""
        if self.conn:
            self.conn.close()
    
    def load_entity_classes(self) -> bool:
        """加载实体类定义"""
        try:
            self.entity_classes = self.table_mapper.generate_all_entities()
            logger.info(f"加载了 {len(self.entity_classes)} 个实体类")
            return True
        except Exception as e:
            logger.error(f"加载实体类失败: {e}")
            return False
    
    def create_instance_from_record(self, table_name: str, record: Dict[str, Any]) -> Optional[OntologyInstance]:
        """从数据库记录创建实体实例"""
        if table_name not in self.entity_classes:
            logger.error(f"未找到实体类: {table_name}")
            return None
        
        entity_class = self.entity_classes[table_name]
        
        # 创建实例名称
        instance_name = record.get('name') or record.get('title') or f"{table_name}_{record.get('id', 'unknown')}"
        
        # 创建实例
        instance = OntologyInstance(
            name=str(instance_name),
            label=f"{entity_class.label}实例",
            definition=f"{entity_class.name}的具体实例",
            instance_of=[entity_class.name],
            property_values=record,
            data_source_id=entity_class.data_source.id if entity_class.data_source else None,
            record_id=str(record.get('id', 'unknown')),
            record_data=record,
            last_sync_time=datetime.now()
        )
        
        # 分析并添加关系
        self._analyze_instance_relationships(instance, entity_class, record)
        
        return instance
    
    def _analyze_instance_relationships(self, instance: OntologyInstance, 
                                      entity_class: OntologyClass, 
                                      record: Dict[str, Any]) -> None:
        """分析实例关系"""
        table_name = entity_class.name
        
        # 分析外键关系
        for prop in entity_class.properties:
            if prop.name.endswith("_id") and prop.name != "id":
                related_table = prop.name[:-3] + "s"
                related_id = record.get(prop.name)
                
                if related_id:
                    relation = {
                        "type": RelationType.FOREIGN_KEY,
                        "subject": instance.name,
                        "object": f"{related_table}_{related_id}",
                        "relation_name": f"has_{related_table}",
                        "confidence": 0.9
                    }
                    instance.relations.append(relation)
        
        # 分析具体的业务关系
        if table_name == "developers":
            self._analyze_developer_relationships(instance, record)
        elif table_name == "projects":
            self._analyze_project_relationships(instance, record)
    
    def _analyze_developer_relationships(self, instance: OntologyInstance, record: Dict[str, Any]) -> None:
        """分析开发者关系"""
        # 团队关系
        if "team_id" in record and record["team_id"]:
            relation = {
                "type": RelationType.PART_OF,
                "subject": instance.name,
                "object": f"teams_{record['team_id']}",
                "relation_name": "member_of_team",
                "confidence": 0.9
            }
            instance.relations.append(relation)
    
    def _analyze_project_relationships(self, instance: OntologyInstance, record: Dict[str, Any]) -> None:
        """分析项目关系"""
        # 项目本身是顶级实体，通常没有直接的外键关系
        pass
    
    def load_all_instances(self) -> bool:
        """加载所有实例"""
        if not self.conn:
            return False
        
        try:
            cursor = self.conn.cursor()
            
            for table_name, entity_class in self.entity_classes.items():
                # 获取表的所有记录
                cursor.execute(f"SELECT * FROM {table_name}")
                records = cursor.fetchall()
                
                # 获取列名
                cursor.execute(f"PRAGMA table_info({table_name})")
                columns = [col[1] for col in cursor.fetchall()]
                
                # 创建实例
                table_instances = []
                for record in records:
                    record_dict = dict(zip(columns, record))
                    instance = self.create_instance_from_record(table_name, record_dict)
                    if instance:
                        table_instances.append(instance)
                
                self.instances[table_name] = table_instances
                logger.info(f"从表 {table_name} 加载了 {len(table_instances)} 个实例")
            
            return True
            
        except Exception as e:
            logger.error(f"加载实例失败: {e}")
            return False
    
    def get_instances_by_class(self, class_name: str) -> List[OntologyInstance]:
        """根据类名获取实例"""
        return self.instances.get(class_name, [])
    
    def get_statistics(self) -> Dict[str, Any]:
        """获取统计信息"""
        stats = {
            "total_classes": len(self.entity_classes),
            "total_instances": sum(len(instances) for instances in self.instances.values()),
            "instances_by_class": {},
            "total_relations": 0
        }
        
        for class_name, instances in self.instances.items():
            stats["instances_by_class"][class_name] = len(instances)
            stats["total_relations"] += sum(len(inst.property_values) for inst in instances)
        
        return stats

class SoftwareEngineeringOntologyDemo:
    """软件工程领域本体演示数据 - 基于数据库模型"""
    
    def __init__(self):
        self.demo = SoftwareEngineeringDemo()
    

    def create_software_engineering_instances(self):
        """从数据库创建软件工程实例"""
        ontology_data = self.demo.build_ontology_from_database()
        if "error" in ontology_data:
            logger.error(f"构建本体失败: {ontology_data['error']}")
            return []
        return ontology_data.get("instances", [])

    def create_software_engineering_relations(self):
        """从实例关系创建语义关系"""
        instances = self.create_software_engineering_instances()
        relations = []
        
        for instance in instances:
            for relation_data in instance.relations:
                relation = SemanticRelation(
                    subject=instance.name,
                    predicate=relation_data.get("relation_name", "related_to"),
                    object=str(relation_data.get("object", "")),
                    relation_type=RelationType(relation_data.get("type", "related_to")),
                    confidence=relation_data.get("confidence", 0.8)
                )
                relations.append(relation)
        
        return relations

class OntologyKnowledgeGraphBuilder:
    """基于数据库的知识图谱构建器 - 基于直接Neo4j实现"""
    
    def __init__(self):
        self.neo4j_connector: Optional[Neo4jConnector] = None
        self.direct_builder: Optional[DirectNeo4jOntologyBuilder] = None
        self.demo: Optional[SoftwareEngineeringDemo] = None
        self.mapper: Optional[DataSourceMapper] = None
        self.entity_manager: Optional[EntityInstanceManager] = None
    
    def initialize(self) -> bool:
        """初始化构建器"""
        try:
            logger.info("初始化基于数据库的知识图谱构建器...")
            
            # 初始化Neo4j连接器
            self.neo4j_connector = Neo4jConnector(NEO4J_URI, NEO4J_USER, NEO4J_PASSWORD)
            
            if not self.neo4j_connector.connect():
                logger.error("无法连接到Neo4j数据库")
                return False
            
            # 初始化直接Neo4j构建器
            self.direct_builder = DirectNeo4jOntologyBuilder()
            
            if not self.direct_builder.connect():
                logger.error("无法连接到Neo4j数据库（直接构建器）")
                return False
            
            # 初始化演示和映射器
            self.demo = SoftwareEngineeringDemo()
            self.mapper = DataSourceMapper()
            
            # 初始化实体实例管理器
            self.entity_manager = EntityInstanceManager("software_engineering.db")
            
            if not self.entity_manager.connect():
                logger.error("无法连接到SQLite数据库（实体管理器）")
                return False
            
            logger.info("基于数据库的知识图谱构建器初始化成功")
            return True
            
        except Exception as e:
            logger.error(f"构建器初始化失败: {e}")
            return False
    
    def demonstrate_database_creation(self):
        """演示数据库创建"""
        print("\n" + "="*60)
        print("演示1: 创建软件工程数据库")
        print("="*60)
        
        if not self.demo.create_database():
            print("数据库创建失败")
            return False
        
        # 获取统计信息
        stats = self.demo.get_database_statistics()
        print(f"\n数据库统计信息:")
        print(f"  - 项目数量: {stats.get('projects_count', 0)}")
        print(f"  - 团队数量: {stats.get('teams_count', 0)}")
        print(f"  - 开发者数量: {stats.get('developers_count', 0)}")
        print(f"  - 需求数量: {stats.get('requirements_count', 0)}")
        print(f"  - 任务数量: {stats.get('tasks_count', 0)}")
        
        # 显示项目状态分布
        project_status = stats.get('project_status_distribution', {})
        print(f"\n项目状态分布:")
        for status, count in project_status.items():
            print(f"  - {status}: {count}个")
        
        return True
    
    def demonstrate_ontology_building(self):
        """演示本体构建"""
        print("\n" + "="*60)
        print("演示2: 基于数据库构建本体")
        print("="*60)
        
        # 从数据库构建本体类
        ontology_data = self.demo.build_ontology_from_database()
        if "error" in ontology_data:
            print(f"构建本体失败: {ontology_data['error']}")
            return False
        
        classes = ontology_data.get("classes", [])
        print(f"\n从数据库创建了 {len(classes)} 个本体类:")
        
        for i, cls in enumerate(classes, 1):
            print(f"\n  {i}. {cls.name} ({cls.label})")
            print(f"     定义: {cls.definition}")
            print(f"     属性数量: {len(cls.properties)}")
            print(f"     数据源: {cls.data_source.name if cls.data_source else '无'}")
            
            # 显示属性
            if cls.properties:
                print(f"     属性: {', '.join([prop.name for prop in cls.properties[:3]])}")
                if len(cls.properties) > 3:
                    print(f"         ... 还有 {len(cls.properties) - 3} 个属性")
        
        # 显示实例信息
        instances = ontology_data.get("instances", [])
        print(f"\n从数据库创建了 {len(instances)} 个实例")
        
        # 显示实例示例
        print(f"\n实例示例:")
        for i, instance in enumerate(instances[:3], 1):
            print(f"  {i}. {instance.name}")
            print(f"     类型: {', '.join(instance.instance_of)}")
            print(f"     数据源ID: {instance.data_source_id}")
            print(f"     记录ID: {instance.record_id}")
            print(f"     关系数量: {len(instance.relations)}")
        
        return True
    
    def demonstrate_relation_analysis(self):
        """演示关系分析"""
        print("\n" + "="*60)
        print("演示3: 关系分析")
        print("="*60)
        
        relations = self.demo.demonstrate_relations()
        print(f"\n自动分析了 {len(relations)} 个关系")
        
        # 按关系类型分组
        relation_types = {}
        for relation in relations:
            rel_type = relation.get("relation_type", "unknown")
            if rel_type not in relation_types:
                relation_types[rel_type] = []
            relation_types[rel_type].append(relation)
        
        print(f"\n关系类型分布:")
        for rel_type, rels in relation_types.items():
            print(f"  - {rel_type}: {len(rels)}个")
        
        # 显示关系示例
        print(f"\n关系示例:")
        for i, relation in enumerate(relations[:5], 1):
            print(f"  {i}. {relation['subject']} --[{relation['relation_name']}]--> {relation['object']}")
            print(f"     类型: {relation['relation_type']}")
            print(f"     置信度: {relation['confidence']}")
        
        return True
    
    def demonstrate_object_oriented_entities(self):
        """演示面向对象实体模型"""
        print("\n" + "="*60)
        print("演示4: 面向对象实体模型")
        print("="*60)
        
        # 加载实体类
        if not self.entity_manager.load_entity_classes():
            print("加载实体类失败")
            return False
        
        entity_classes = self.entity_manager.entity_classes
        print(f"\n生成了 {len(entity_classes)} 个面向对象实体类:")
        
        for class_name, entity_class in entity_classes.items():
            print(f"\n  {class_name} 类:")
            print(f"     定义: {entity_class.definition}")
            print(f"     属性数量: {len(entity_class.properties)}")
            print(f"     方法数量: {len(entity_class.methods)}")
            print(f"     数据源: {entity_class.data_source.name if entity_class.data_source else '无'}")
            
            # 显示属性示例
            if entity_class.properties:
                print(f"     属性示例:")
                for prop in entity_class.properties[:3]:
                    print(f"       - {prop.name}: {prop.range_type} ({'必需' if prop.is_required else '可选'})")
                if len(entity_class.properties) > 3:
                    print(f"       ... 还有 {len(entity_class.properties) - 3} 个属性")
            
            # 显示方法示例
            if entity_class.methods:
                print(f"     方法示例:")
                for method in entity_class.methods[:3]:
                    params = ', '.join([f"{p['name']}: {p['type']}" for p in method.parameters])
                    print(f"       - {method.name}({params}) -> {method.return_type}")
                if len(entity_class.methods) > 3:
                    print(f"       ... 还有 {len(entity_class.methods) - 3} 个方法")
        
        return True
    
    def demonstrate_instance_management(self):
        """演示实例管理"""
        print("\n" + "="*60)
        print("演示5: 实体实例管理")
        print("="*60)
        
        # 加载所有实例
        if not self.entity_manager.load_all_instances():
            print("加载实例失败")
            return False
        
        # 显示实例统计
        stats = self.entity_manager.get_statistics()
        print(f"\n实例统计信息:")
        print(f"  - 总类数: {stats['total_classes']}")
        print(f"  - 总实例数: {stats['total_instances']}")
        print(f"  - 总关系数: {stats['total_relations']}")
        
        print(f"\n各类实例数量:")
        for class_name, count in stats['instances_by_class'].items():
            print(f"  - {class_name}: {count}个")
        
        # 显示实例示例
        print(f"\n实例示例:")
        for class_name, instances in self.entity_manager.instances.items():
            if instances:
                instance = instances[0]
                print(f"\n  {class_name} 实例: {instance.name}")
                print(f"     类型: {', '.join(instance.instance_of)}")
                print(f"     记录ID: {instance.record_id}")
                print(f"     关系数量: {len(instance.relations)}")
                
                # 显示属性值示例
                if instance.property_values:
                    print(f"     属性值示例:")
                    for key, value in list(instance.property_values.items())[:3]:
                        print(f"       - {key}: {value}")
                    if len(instance.property_values) > 3:
                        print(f"       ... 还有 {len(instance.property_values) - 3} 个属性")
        
        return True
    
    def demonstrate_instance_of_relationships(self):
        """演示INSTANCE_OF关系"""
        print("\n" + "="*60)
        print("演示6: INSTANCE_OF关系管理")
        print("="*60)
        
        # 获取所有实例
        all_instances = []
        for instances in self.entity_manager.instances.values():
            all_instances.extend(instances)
        
        print(f"\n分析了 {len(all_instances)} 个实例的INSTANCE_OF关系")
        
        # 按类分组显示实例
        class_instances = {}
        for instance in all_instances:
            for class_name in instance.instance_of:
                if class_name not in class_instances:
                    class_instances[class_name] = []
                class_instances[class_name].append(instance)
        
        print(f"\nINSTANCE_OF关系分布:")
        for class_name, instances in class_instances.items():
            print(f"  - {class_name}: {len(instances)}个实例")
        
        # 显示关系示例
        print(f"\nINSTANCE_OF关系示例:")
        for class_name, instances in list(class_instances.items())[:3]:
            print(f"\n  {class_name} 类的实例:")
            for i, instance in enumerate(instances[:3], 1):
                print(f"    {i}. {instance.name} INSTANCE_OF {class_name}")
                if instance.relations:
                    print(f"       关系: {len(instance.relations)}个")
            if len(instances) > 3:
                print(f"    ... 还有 {len(instances) - 3} 个实例")
        
        return True
    
    def build_knowledge_graph(self):
        """构建知识图谱"""
        print("\n" + "="*60)
        print("演示7: 构建知识图谱")
        print("="*60)
        
        try:
            logger.info("开始构建基于直接Neo4j的知识图谱...")
            
            # 1. 先构建基础知识图谱
            self.direct_builder.build_ontology_from_sqlite("software_engineering.db")
            
            # 2. 添加实体类节点和INSTANCE_OF关系
            self._create_entity_class_nodes()
            self._create_instance_of_relationships()
            
            # 3. 验证知识图谱
            self._verify_enhanced_ontology()
            
            logger.info("知识图谱构建完成")
            return True
        except Exception as e:
            logger.error(f"知识图谱构建失败: {e}")
            return False
    
    def _create_entity_class_nodes(self):
        """创建实体类节点"""
        print("\n创建实体类节点...")
        
        with self.direct_builder.driver.session() as session:
            # 创建Developer类节点
            session.run("""
                CREATE (dc:EntityClass {
                    name: 'Developer',
                    label: '开发者',
                    definition: '软件工程中的开发者实体，代表参与项目开发的人员',
                    namespace: 'software_engineering',
                    concept_type: 'Class',
                    properties: [
                        'id:integer:required:unique',
                        'name:string:required',
                        'email:string:required:unique',
                        'role:string:optional',
                        'experience_years:integer:optional',
                        'team_id:integer:optional',
                        'created_at:datetime:required'
                    ],
                    methods: [
                        'assign_to_team(team_id:integer):boolean',
                        'get_team_members():List[Developer]',
                        'calculate_experience_level():string'
                    ],
                    class_variables: 'DEFAULT_ROLE:developer,MAX_EXPERIENCE_YEARS:50'
                })
            """)
            
            # 创建Project类节点
            session.run("""
                CREATE (pc:EntityClass {
                    name: 'Project',
                    label: '项目',
                    definition: '软件工程项目实体，代表一个完整的软件开发项目',
                    namespace: 'software_engineering',
                    concept_type: 'Class',
                    properties: [
                        'id:integer:required:unique',
                        'name:string:required',
                        'description:string:optional',
                        'status:string:required',
                        'start_date:datetime:required',
                        'end_date:datetime:optional',
                        'created_at:datetime:required'
                    ],
                    methods: [
                        'add_team(team:Team):boolean',
                        'get_all_teams():List[Team]',
                        'calculate_progress():float'
                    ],
                    class_variables: 'VALID_STATUSES:planning,active,on_hold,completed,cancelled;DEFAULT_STATUS:planning'
                })
            """)
            
            # 创建Team类节点
            session.run("""
                CREATE (tc:EntityClass {
                    name: 'Team',
                    label: '团队',
                    definition: '软件开发团队实体，包含多个开发者和一个负责人',
                    namespace: 'software_engineering',
                    concept_type: 'Class',
                    properties: [
                        'id:integer:required:unique',
                        'name:string:required',
                        'description:string:optional',
                        'project_id:integer:required',
                        'leader_id:integer:required',
                        'created_at:datetime:required'
                    ],
                    methods: [
                        'add_member(developer:Developer):boolean',
                        'get_members():List[Developer]',
                        'get_leader():Optional[Developer]'
                    ]
                })
            """)
            
            # 创建Requirement类节点
            session.run("""
                CREATE (rc:EntityClass {
                    name: 'Requirement',
                    label: '需求',
                    definition: '软件需求实体，代表项目的功能需求或非功能需求',
                    namespace: 'software_engineering',
                    concept_type: 'Class',
                    properties: [
                        'id:integer:required:unique',
                        'title:string:required',
                        'description:text:required',
                        'project_id:integer:required',
                        'priority:string:required',
                        'status:string:required',
                        'assigned_to:integer:optional',
                        'created_at:datetime:required',
                        'due_date:datetime:optional'
                    ],
                    methods: [
                        'assign_to_developer(developer_id:integer):boolean',
                        'get_related_tasks():List[Task]',
                        'update_status(new_status:string):boolean'
                    ]
                })
            """)
            
            # 创建Task类节点
            session.run("""
                CREATE (tac:EntityClass {
                    name: 'Task',
                    label: '任务',
                    definition: '开发任务实体，代表实现需求的具体工作项',
                    namespace: 'software_engineering',
                    concept_type: 'Class',
                    properties: [
                        'id:integer:required:unique',
                        'title:string:required',
                        'description:text:optional',
                        'requirement_id:integer:required',
                        'assigned_to:integer:required',
                        'status:string:required',
                        'priority:string:required',
                        'estimated_hours:decimal:optional',
                        'actual_hours:decimal:optional',
                        'created_at:datetime:required',
                        'due_date:datetime:optional',
                        'completed_at:datetime:optional'
                    ],
                    methods: [
                        'assign_to_developer(developer_id:integer):boolean',
                        'start_work():boolean',
                        'complete_task():boolean',
                        'update_progress(progress_percent:float):boolean'
                    ]
                })
            """)
            
            print("实体类节点创建完成")
    
    def _create_instance_of_relationships(self):
        """创建INSTANCE_OF关系"""
        print("\n创建INSTANCE_OF关系...")
        
        with self.direct_builder.driver.session() as session:
            # 创建Developer实例的INSTANCE_OF关系
            session.run("""
                MATCH (dc:EntityClass {name: 'Developer'}), (d:Developer)
                CREATE (d)-[:INSTANCE_OF]->(dc)
            """)
            
            # 创建Project实例的INSTANCE_OF关系
            session.run("""
                MATCH (pc:EntityClass {name: 'Project'}), (p:Project)
                CREATE (p)-[:INSTANCE_OF]->(pc)
            """)
            
            # 创建Team实例的INSTANCE_OF关系
            session.run("""
                MATCH (tc:EntityClass {name: 'Team'}), (t:Team)
                CREATE (t)-[:INSTANCE_OF]->(tc)
            """)
            
            # 创建Requirement实例的INSTANCE_OF关系
            session.run("""
                MATCH (rc:EntityClass {name: 'Requirement'}), (r:Requirement)
                CREATE (r)-[:INSTANCE_OF]->(rc)
            """)
            
            # 创建Task实例的INSTANCE_OF关系
            session.run("""
                MATCH (tac:EntityClass {name: 'Task'}), (t:Task)
                CREATE (t)-[:INSTANCE_OF]->(tac)
            """)
            
            print("INSTANCE_OF关系创建完成")
    
    def _verify_enhanced_ontology(self):
        """验证增强的本体知识图谱"""
        print("\n=== 增强本体知识图谱验证 ===")
        
        with self.direct_builder.driver.session() as session:
            # 统计节点数量
            result = session.run("MATCH (n) RETURN labels(n)[0] as label, count(n) as count")
            print("节点统计:")
            for record in result:
                print(f"  {record['label']}: {record['count']}个")
            
            # 统计关系数量
            result = session.run("MATCH ()-[r]->() RETURN type(r) as type, count(r) as count")
            print("\n关系统计:")
            for record in result:
                print(f"  {record['type']}: {record['count']}个")
            
            # 验证实体类节点
            print("\n实体类节点:")
            result = session.run("MATCH (ec:EntityClass) RETURN ec.name, ec.label, ec.definition")
            for record in result:
                print(f"  - {record['ec.name']} ({record['ec.label']}): {record['ec.definition']}")
            
            # 验证INSTANCE_OF关系
            print("\nINSTANCE_OF关系示例:")
            result = session.run("""
                MATCH (i)-[:INSTANCE_OF]->(ec:EntityClass)
                RETURN i.name as instance_name, labels(i)[0] as instance_type, ec.name as class_name
                LIMIT 10
            """)
            for record in result:
                print(f"  - {record['instance_name']} ({record['instance_type']}) INSTANCE_OF {record['class_name']}")
            
            # 验证数据完整性
            print("\n数据完整性检查:")
            
            # 检查项目
            result = session.run("MATCH (p:Project) RETURN p.name, p.status ORDER BY p.id LIMIT 5")
            print("项目实例:")
            for record in result:
                print(f"  - {record['p.name']} ({record['p.status']})")
            
            # 检查开发者
            result = session.run("MATCH (d:Developer) RETURN d.name, d.role, d.team_id ORDER BY d.id LIMIT 5")
            print("开发者实例:")
            for record in result:
                print(f"  - {record['d.name']} ({record['d.role']}, 团队ID: {record['d.team_id']})")
    
    def cleanup(self):
        """清理资源"""
        try:
            if self.neo4j_connector:
                self.neo4j_connector.close()
                logger.info("Neo4j连接已关闭")
            if self.direct_builder:
                self.direct_builder.close()
                logger.info("直接构建器连接已关闭")
            if self.entity_manager:
                self.entity_manager.close()
                logger.info("实体管理器连接已关闭")
        except Exception as e:
            logger.error(f"清理资源失败: {e}")

def main():
    """主函数 - 构建和演示基于数据库的知识图谱"""
    builder = OntologyKnowledgeGraphBuilder()
    
    try:
        print("面向对象知识图谱构建演示开始！")
        print("="*80)
        
        # 初始化构建器
        if not builder.initialize():
            logger.error("构建器初始化失败，退出程序")
            sys.exit(1)
        
        # 演示1: 数据库创建
        builder.demonstrate_database_creation()
        
        # 演示2: 基于数据库的本体构建
        builder.demonstrate_ontology_building()
        
        # 演示3: 关系分析
        builder.demonstrate_relation_analysis()
        
        # 演示4: 面向对象实体模型
        builder.demonstrate_object_oriented_entities()
        
        # 演示5: 实体实例管理
        builder.demonstrate_instance_management()
        
        # 演示6: INSTANCE_OF关系管理
        builder.demonstrate_instance_of_relationships()
        
        # 演示7: 构建知识图谱
        if not builder.build_knowledge_graph():
            logger.error("知识图谱构建失败，退出程序")
            sys.exit(1)
        
        print("\n" + "="*80)
        print("面向对象知识图谱构建完成！")
        print("\n主要特性总结:")
        print("  - 基于数据库表的自动本体构建")
        print("  - 实例与数据源记录的直接绑定")
        print("  - 从表字段自动分析建立关系")
        print("  - 支持多种数据源类型 (SQLite、API、消息队列)")
        print("  - 直接基于Neo4j的知识图谱构建")
        print("  - 数据完全一致，无外部干扰")
        print("  - 面向对象实体模型支持")
        print("  - 支持INSTANCE_OF关系管理")
        print("  - 完整的实体类定义（属性、方法、继承）")
        print("  - 自动实例关系分析和管理")
        
    except KeyboardInterrupt:
        print("\n用户中断演示")
        logger.info("用户中断程序")
    except Exception as e:
        logger.error(f"程序运行出错: {e}")
        import traceback
        traceback.print_exc()
    finally:
        builder.cleanup()

if __name__ == "__main__":
    main()