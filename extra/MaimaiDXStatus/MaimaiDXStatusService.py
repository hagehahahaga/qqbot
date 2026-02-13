from abstract.bases.importer import datetime, threading, requests, local_time, io, PIL, matplotlib, itertools
from abstract.bases import PIL_FONT
from typing import Optional


class MaimaiDXStatusService:
    def __init__(self):
        self._update_time: Optional[datetime.datetime] = None
        self._nodes: Optional[dict[str, MaimaiDXNode]] = None
        self._got_data = threading.Event()
        self._nodes_status: dict[str, MaimaiDXNodeStatus] = {}
        self.ready = False

    @property
    def result(self) -> tuple[datetime.datetime, dict[str, MaimaiDXNode]]:
        self._got_data.wait()
        return self._update_time, self._nodes

    def update_status(self) -> dict[str, MaimaiDXNodeStatus]:
        self._update_time = local_time()
        try:
            self._nodes = {
                id: MaimaiDXNode(id, data) for id, data in
                requests.get(
                    url='https://status.awmc.cc/api/status-page/heartbeat/maimai',
                    headers={
                        'User-Agent': 'SouTuBot'
                    }
                ).json()['heartbeatList'].items()
            }
        except Exception as e:
            self.ready = False
            raise e
        self._got_data.set()
        self.ready = True
        output = {}
        for node in self._nodes.values():
            if self._nodes_status.get(node.ID) is None:
                self._nodes_status[node.ID] = node.STATUSES[-1]
                continue
            try:
                earliest_inequal_status = list(
                    itertools.takewhile(
                        lambda a: a.STATUS_CODE != self._nodes_status[node.ID].STATUS_CODE and
                                  a.STATUS_CODE == node.STATUSES[-1].STATUS_CODE,
                        node.STATUSES[::-1]
                    )
                )[-1]
            except IndexError:
                continue
            if (node.STATUSES[-1].TIME - earliest_inequal_status.TIME).total_seconds() / 60 > 5:
                output[node.NAME] = earliest_inequal_status.STATUS
                self._nodes_status[node.ID] = node.STATUSES[-1]
        return output

    def render(self, night: bool = False) -> bytes:
        """
        渲染所有服务状态为图像，将所有节点的状态从上到下拼接

        :param night: 是否使用黑底白字
        :type night: bool
        :return: 图像字节数据
        :rtype: bytes
        """
        # 使用 self.result 获取更新时间和节点列表
        update_time, all_nodes = self.result
        
        # 过滤节点：只保留以 "[上海电信代理]" 结尾或名称为 "舞萌DX服务" 的节点
        nodes = [
            node for node in all_nodes.values()
            if node.NAME.endswith("[上海电信代理]") or node.NAME == "舞萌DX状态"
        ]
        
        # 创建顶部更新时间图像
        width = 2400
        header_height = 100
        warning_height = 100 if not self.ready else 0
        footer_height = 100
        if night:
            bg_color = (0, 0, 0)
            text_color = (255, 255, 255)
        else:
            bg_color = (255, 255, 255)
            text_color = (0, 0, 0)
        
        # 创建警告图像（如果需要）
        if not self.ready:
            warning_image = PIL.Image.new('RGB', (width, warning_height), bg_color)
            warning_draw = PIL.ImageDraw.Draw(warning_image)
            warning_font = PIL_FONT.font_variant(size=48)
            warning_text = "API暂时不可用, 使用缓存数据, 注意数据时间"
            warning_draw.text((50, 25), warning_text, font=warning_font, fill=(255, 0, 0))  # 红色警告文字
        
        # 创建顶部更新时间图像
        header_image = PIL.Image.new('RGB', (width, header_height), bg_color)
        draw = PIL.ImageDraw.Draw(header_image)
        font = PIL_FONT.font_variant(size=48)
        
        # 绘制更新时间
        time_text = f"更新时间: {update_time.strftime('%Y-%m-%d %H:%M:%S')}"
        draw.text((50, 25), time_text, font=font, fill=text_color)
        
        # 创建底部数据来源图像
        footer_image = PIL.Image.new('RGB', (width, footer_height), bg_color)
        footer_draw = PIL.ImageDraw.Draw(footer_image)
        footer_font = PIL_FONT.font_variant(size=48)
        footer_text = "数据来源status.awmc.cc"
        footer_draw.text((50, 25), footer_text, font=footer_font, fill=text_color)
        
        # 获取每个节点的渲染结果
        node_images = []
        for node in nodes:
            node_bytes = node.render(night)
            node_image = PIL.Image.open(io.BytesIO(node_bytes))
            node_images.append(node_image)
        
        # 计算总高度
        total_height = warning_height + header_height + sum(img.height for img in node_images) + footer_height
        
        # 创建拼接图像
        result_image = PIL.Image.new('RGB', (width, total_height), bg_color)
        
        # 拼接图像
        current_y = 0
        # 粘贴警告图像（如果需要）
        if not self.ready:
            result_image.paste(warning_image, (0, current_y))
            current_y += warning_height
        # 粘贴顶部更新时间图像
        result_image.paste(header_image, (0, current_y))
        current_y += header_height
        
        # 粘贴每个节点的图像
        for img in node_images:
            result_image.paste(img, (0, current_y))
            current_y += img.height
        
        # 粘贴底部数据来源图像
        result_image.paste(footer_image, (0, current_y))
        
        # 保存为字节
        byte_arr = io.BytesIO()
        result_image.save(byte_arr, format='PNG')
        return byte_arr.getvalue()


class MaimaiDXNode:
    NAME_MAPPING = {
    '1': '舞萌DX状态',
    '4': 'NET服务器 [上海联通代理]',
    '5': '游戏标题服务器 [上海联通代理]',
    '6': '游戏标题服务器 [上海电信代理]',
    '7': '游戏标题服务器 [上海移动代理]',
    '8': '二维码服务器 [上海联通代理]',
    '9': '二维码服务器 [上海电信代理]',
    '10': '二维码服务器 [上海移动代理]',
    '11': 'ALL.NET机台管理服务器 [上海联通代理]',
    '12': 'ALL.NET机台管理服务器 [上海电信代理]',
    '13': 'ALL.NET机台管理服务器 [上海移动代理]',
    '14': '会员服务器 [上海电信代理]',
    '15': '会员服务器 [上海移动代理]',
    '16': '会员服务器 [上海联通代理]',
    '17': 'NET服务器 [上海电信代理]',
    '18': 'NET服务器 [上海移动代理]'
}

    def __init__(self, id: str, data: list[dict]):
        self.ID: str = id
        self.NAME: str = self.NAME_MAPPING[id]
        self.STATUSES: list[MaimaiDXNodeStatus] = list(map(MaimaiDXNodeStatus, data))

    def render(self, night: bool = False) -> bytes:
        """
        渲染服务状态为图像

        :param night: 是否使用黑底白字
        :type night: bool
        :return: 图像字节数据
        :rtype: bytes
        """
        # 配置
        width, height = 2400, 400
        
        # 使用比例而非固定像素值
        padding_ratio = 0.02  # 内边距比例
        bar_height_ratio = 0.2   # 状态栏高度比
        status_bar_y_ratio = 0.35 # 状态栏Y坐标比例
        time_info_y_offset_ratio = 0.05 # 时间信息Y坐标偏移比例
        font_size_ratio = 0.0267 # 字体大小比例
        
        padding = width * padding_ratio
        bar_height = height * bar_height_ratio
        bar_width = width - 2 * padding

        # 创建图像
        if night:
            bg_color = (0, 0, 0)
            text_color = (255, 255, 255)
        else:
            bg_color = (255, 255, 255)
            text_color = (0, 0, 0)

        image = PIL.Image.new('RGB', (width, height), bg_color)
        draw = PIL.ImageDraw.Draw(image)

        # 创建更大字号的字体变体
        font_size = width * font_size_ratio
        font = PIL_FONT.font_variant(size=int(font_size))

        # 绘制服务名称
        draw.text((padding, padding),self.ID + ' - ' +  self.NAME, font=font, fill=text_color)
        
        # 绘制状态条 - 每个色块对应一个时间的状态
        status_bar_y = height * status_bar_y_ratio
        
        # 只取最后100个状态
        recent_statuses = self.STATUSES[-100:] if self.STATUSES else []
        status_count = len(recent_statuses)

        # 计算每个色块的宽度（间隙为色块宽度的30%）
        block_width = bar_width / (status_count + 0.3 * (status_count - 1))
        # 设置色块间隙为色块宽度的30%
        gap = block_width * 0.3

        # 为每个状态绘制色块
        for i, status in enumerate(recent_statuses):
            # 确定色块颜色
            if status.STATUS == '稳定':
                block_color = (0, 255, 0)  # 绿色 - 正常
            elif status.STATUS == '不稳定':
                block_color = (255, 255, 0)  # 黄色 - 不稳定
            else:
                block_color = (255, 0, 0)  # 红色 - 异常

            # 计算色块位置（包含间隙）
            block_x = padding + i * (block_width + gap)

            # 绘制圆角色块
            radius = block_width / 2  # 圆角半径为色块宽度的一半
            draw.rounded_rectangle([(block_x, status_bar_y), (block_x + block_width, status_bar_y + bar_height)],
                                   radius=radius, fill=block_color)
        
        # 绘制时间信息
        time_info_y = status_bar_y + bar_height + height * time_info_y_offset_ratio
        # 计算时间差（分钟）
        earliest_time_diff = int((local_time() - self.STATUSES[0].TIME).total_seconds() / 60)
        latest_time_diff = int((local_time() - self.STATUSES[-1].TIME).total_seconds() / 60)
        if latest_time_diff:
            latest_text = f"{latest_time_diff}分钟前"
        else:
            latest_text = "现在"
        draw.text((padding, time_info_y), f"{earliest_time_diff}分钟前", font=font, fill=text_color)
        
        # 计算文本宽度，实现右侧对齐
        text_bbox = draw.textbbox((0, 0), latest_text, font=font)
        text_width = text_bbox[2] - text_bbox[0]
        right_x = width - padding - text_width
        draw.text((right_x, time_info_y), latest_text, font=font, fill=text_color)
        
        # 保存为字节
        byte_arr = io.BytesIO()
        image.save(byte_arr, format='PNG')
        return byte_arr.getvalue()

    def stat_render(self) -> bytes:
        """
        渲染服务状态的 ping 统计为散点图

        :return: 图像字节数据
        :rtype: bytes
        """
        # 配置
        width, height = 1200, 600
        footer_height = 80

        # 准备数据
        all_times = []  # 所有时间点（包括ping为None的）
        valid_times = []  # ping不为None的时间点
        valid_pings = []  # ping不为None的ping值
        
        for status in self.STATUSES:
            all_times.append(status.TIME)
            if status.PING is not None:
                valid_times.append(status.TIME)
                valid_pings.append(status.PING)
        
        # 创建图形
        fig, ax = matplotlib.pyplot.subplots(figsize=(width/100, (height + footer_height)/100), dpi=100)
        
        # 计算时间范围（使用所有时间点）
        start_time = all_times[0]
        end_time = all_times[-1]

        # 转换时间为相对时间（分钟）
        relative_valid_times = [(end_time - t).total_seconds() / 60 for t in valid_times]
        # 绘制散点图（只使用ping不为None的数据）
        ax.scatter(relative_valid_times, valid_pings, s=50, alpha=0.7)
        
        # 设置横坐标范围（使用所有时间点的范围）
        total_duration = (end_time - start_time).total_seconds() / 60
        ax.set_xlim(-5, total_duration + 5)
        
        # 添加网格
        ax.grid(True, linestyle='--', alpha=0.7)

        # 反转x轴
        ax.invert_xaxis()
        
        # 设置y轴为对数刻度
        ax.set_yscale('log')
        
        # 设置y轴刻度为正常数字格式（非科学计数法）
        ax.yaxis.set_major_formatter(matplotlib.ticker.ScalarFormatter())
        ax.yaxis.set_minor_formatter(matplotlib.ticker.ScalarFormatter())
        
        # 设置标题和标签
        ax.set_title(f'{self.ID} - {self.NAME} Ping 统计', fontsize=24)
        ax.set_xlabel('时间（分钟）', fontsize=18)
        ax.set_ylabel('Ping（毫秒，对数刻度）', fontsize=18)
        
        # 设置刻度颜色
        ax.tick_params(axis='both', labelsize=14)
        
        # 调整布局，为页脚留出空间
        matplotlib.pyplot.subplots_adjust(top=0.9, bottom=0.15)
        
        # 添加数据来源信息
        fig.text(0.05, 0.05, '数据来源status.awmc.cc', fontsize=14)
        
        # 保存为字节
        byte_arr = io.BytesIO()
        matplotlib.pyplot.savefig(byte_arr, format='PNG')
        matplotlib.pyplot.close()
        
        return byte_arr.getvalue()



class MaimaiDXNodeStatus:
    STATUS_MAPPING = {
        0: '死了',
        1: '稳定',
        2: '不稳定'
    }

    def __init__(self, data: dict):
        self.STATUS_CODE: int = data['status']
        self.STATUS: str = self.STATUS_MAPPING[self.STATUS_CODE]
        self.PING: int = data['ping']
        self.TIME = datetime.datetime.strptime(
            data['time'], '%Y-%m-%d %H:%M:%S.%f'
        ).replace(tzinfo=datetime.timezone.utc).astimezone()


MAIMAIDX_STATUS_SERVICE = MaimaiDXStatusService()
