#  Copyright 2025 Haruna5718
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

from __future__ import annotations
import sys
sys.dont_write_bytecode = True

from pathlib import Path
import importlib.util

import xml.etree.ElementTree
import json
import gc
import re

from typing import *
from dataclasses import dataclass, field, asdict, is_dataclass, replace

VAILD_DATAS={
	"Vertical":{ # 수평 방향으로 Child를 정렬합니다
		"Text":False,
		"Child":True,
		"Attr":["gap"]
	},
	"Horizontal":{ # 수직 방향으로 Child를 정렬합니다
		"Text":False,
		"Child":True,
		"Attr":["gap"]
	},
	"Box":{ # 기본적으로 수직 방향으로 Child를 정렬하는 배경색이 있는 박스입니다.
		"Text":False,
		"Child":True,
		"Attr":["background","height","width","padding","margin","round","gap"]
	},
	"Space":{ # 가질수 있는 최대한의 너비를 가지는 빈 공간입니다.
		"Text":False,
		"Child":False,
		"Attr":[]
	},
	"Text":{ # type 스타일을 가지는 텍스트입니다. value값과 동기화 할 수 있습니다.
		"Text":True,
		"Child":False,
		"Attr":["type","color","size","margin","disable"]
	},
	"Line":{ # 라인입니다. 정렬 방향의 영향을 받습니다.
		"Text":False,
		"Child":False,
		"Attr":["thin","color","margin"]
	},
	"Button":{ # 푸시 버튼입니다. 
		"Text":True,
		"Child":True,
		"Attr":["value","color","size","background","height","width","padding","margin","round","disable"]
	},
	"Switch":{ # 토글 슬라이드 스위치입니다. value의 값과 동기화됩니다.
		"Text":False,
		"Child":False,
		"Attr":["value","color","margin","disable","aligin"]
	},
	"Input":{ # 텍스트 인풋입니다. value의 값과 동기화되며 type의 속성을 가집니다.
		"Text":False,
		"Child":False,
		"Attr":["type","value","color","background","height","width","padding","margin","round","disable"]
	},
	"Select":{ # 드롭다운 셀렉트 메뉴입니다. value의 값과 index가 동기화되며 opeions중 하나를 선택할수 있습니다.
		"Text":False,
		"Child":False,
		"Attr":["value","options","color","background","height","width","padding","margin","round","disable"]
	},
	"Repeat":{ # Child를 value만큼 반복합니다. Child의 event와 value의 {index}자리에 index가 대체됩니다.
		"Text":False,
		"Child":True,
		"Attr":["value"]
	},
	"If":{ # value가 참이라면 표시하고 거짓이라면 표시하지 않습니다.
		"Text":False,
		"Child":True,
		"Attr":["value"]
	},
	"True":{
		"Text":False,
		"Child":True,
		"Attr":[]
	},
	"False":{
		"Text":False,
		"Child":True,
		"Attr":[]
	},
}

@dataclass
class PageDataType:
	Type: str
	Attr: dict[str,str]
	Text: list[LayoutTextType]
	Children: list[PageDataType]

@dataclass
class LayoutTextType:
	Type: Literal["Icon", "Text"]
	Text: str

@dataclass
class ModuleInfoType:
	DisplayName: str
	DisplayIcon: str
	Version: str
	Author: str
	Description: str
	Url: list[dict[str,str]]
	LayoutPath: str
	FunctionPath: str

@dataclass
class ModuleDataType:
	DisplayName: str
	DisplayIcon: str
	Version: str
	Author: str
	Description: str
	Url: list[dict[str,str]]
	ModulePath: str
	LayoutPath: str
	FunctionPath: str
	Layout: PageDataType
	Function: Any

class XamlParseError(Exception):
	def __init__(self, message):
		super().__init__(message)

class InvaildLayoutError(Exception):
	def __init__(self, message):
		super().__init__(message)

class ModuleNotFound(Exception):
	def __init__(self, message):
		super().__init__(message)

class ModuleError(Exception):
	def __init__(self, message):
		super().__init__(message)

def XamlToJson(Element:xml.etree.ElementTree.Element) -> PageDataType:
	if Element.tag not in VAILD_DATAS.keys():
		raise InvaildLayoutError(f"Not Allowed This Tag: {Element.tag}")
	
	if (Text:=Element.text.strip() if Element.text else "") and not VAILD_DATAS[Element.tag]['Text']:
		raise InvaildLayoutError(f"Text Not Allowed in This Tag: {Element.tag}")
	
	if (Childs:=list(Element)) and not VAILD_DATAS[Element.tag]["Child"]:
		raise InvaildLayoutError(f"Children Not Allowed in This Tag: {Element.tag}")
	
	if WrongAttr:=list(set(Element.attrib.keys()) - set(VAILD_DATAS[Element.tag]['Attr'])):
		raise InvaildLayoutError(f"This Attr Not Allowed in {Element.tag}: {','.join(WrongAttr)}")
	
	return PageDataType(
		Type=Element.tag,
		Attr=Element.attrib,
		Text=Text,
		Children=[XamlToJson(Child) for Child in Childs]
	)

def LoadXaml(FilePath) -> PageDataType:
	try:
		DataRoot = xml.etree.ElementTree.parse(FilePath).getroot()

		ParsedData = XamlToJson(DataRoot)

		return ParsedData
	except xml.etree.ElementTree.ParseError as e:
		raise XamlParseError(e)

def LoadModule(ModulePath:Path,window) -> ModuleDataType:
	try:
		with open(Path(ModulePath)/"ModuleInfo.json", "r", encoding="UTF-8") as file:
			ModuleInfo = ModuleInfoType(**json.load(file))
	except FileNotFoundError as e:
		raise ModuleNotFound(f"ModuleInfo File Not Found: ModuleInfo.json")
	
	try:
		Spec = importlib.util.spec_from_file_location(Path(ModuleInfo.FunctionPath).stem,Path(ModulePath)/ModuleInfo.FunctionPath)
		Module = importlib.util.module_from_spec(Spec)
		Spec.loader.exec_module(Module)
	except FileNotFoundError as e:
		raise ModuleNotFound(f"Function File Not Found: {ModuleInfo.FunctionPath}")
	except ImportError as e:
		raise ModuleError(f"Module Raise ImportError: {e}")
	except Exception as e:
		raise ModuleError(f"Module Raise Error: {e}")

	MainClass=getattr(Module,"MainClass")()
	MainClass.window = window

	return ModuleDataType(
		**asdict(ModuleInfo),
		ModulePath=ModulePath,
		Layout=LoadXaml(Path(ModulePath)/ModuleInfo.LayoutPath),
		Function=MainClass
	)
	
def UnloadModule(ModuleName):
	if ModuleName in sys.modules:
		del sys.modules[ModuleName]
		gc.collect()
	else:
		raise ModuleNotFound(ModuleName)