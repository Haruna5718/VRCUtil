# Copyright 2025 Haruna5718
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

from pathlib import Path
import os, sys

isDebug = not getattr(sys, 'frozen', False)

APPROOT_PATH = Path(__file__).parent.resolve() if isDebug else Path(os.getenv('LOCALAPPDATA'))/'Haruna5718'/'VRCUtil'
MODULES_PATH = APPROOT_PATH/'Modules'

VERSION = "2.0.0"

REPO_URL = "https://api.github.com/repos/Haruna5718/VRCUtil/releases/latest"

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
		"Attr":["background","height","width","padding","margin","round","gap", "fit"]
	},
	"Space":{ # 가질수 있는 최대한의 너비를 가지는 빈 공간입니다.
		"Text":False,
		"Child":False,
		"Attr":["size"]
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
		"Attr":["value","color","size","background","height","width","padding","margin","round","disable","type"]
	},
	"Switch":{ # 토글 슬라이드 스위치입니다. value의 값과 동기화됩니다.
		"Text":False,
		"Child":False,
		"Attr":["value","color","margin","disable","aligin"]
	},
	"Input":{ # 텍스트 인풋입니다. value의 값과 동기화되며 type의 속성을 가집니다.
		"Text":False,
		"Child":False,
		"Attr":["type","value","color","background","height","width","padding","margin","round","disable","max","min"]
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