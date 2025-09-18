"""
Узлы для создания графиков по тикерам в Tinkoff
Универсальный модуль для работы с любыми акциями
"""

import logging
from typing import Annotated, Dict, Any, List, Optional, Tuple
from datetime import datetime, timedelta
from io import BytesIO
import base64

from langchain_core.tools import tool
from langgraph.prebuilt import InjectedState

from ..utils.tinkoff_client import get_tinkoff_client
from ..config import POPULAR_STOCKS

logger = logging.getLogger(__name__)

# Расширенный список популярных российских акций
EXTENDED_POPULAR_STOCKS = {
    **POPULAR_STOCKS,
    "MOEX": {"name": "Московская биржа", "figi": "BBG004730N88"},
    "RUAL": {"name": "РУСАЛ", "figi": "BBG00F9XX7H4"},
    "PHOR": {"name": "ФосАгро", "figi": "BBG004S683W7"},
    "AFLT": {"name": "Аэрофлот", "figi": "BBG00RPRPX12"},
    "MVID": {"name": "М.Видео", "figi": "BBG008F2T3T2"},
    "OZON": {"name": "OZON", "figi": "BBG00F6NKQX3"},
    "QIWI": {"name": "QIWI", "figi": "BBG004731354"},
    "PLZL": {"name": "Полюс", "figi": "BBG004730ZJ9"},
    "RASP": {"name": "Распадская", "figi": "BBG004S68614"},
    "LENT": {"name": "Лента", "figi": "BBG000B9XRY4"},
    "DSKY": {"name": "Детский мир", "figi": "BBG000B9X8T8"},
    "FIVE": {"name": "X5 Retail", "figi": "BBG004S68473"},
    "RENI": {"name": "Ренессанс Страхование", "figi": "BBG000Q7Y2C0"},
    "VKCO": {"name": "VK", "figi": "BBG000FWGSZ5"}
}

async def plot_ticker_chart(ticker: str, timeframe: str = "1day", num_candles: int = 40):
    """
    Рисует простой график по тикеру с объемами
    
    Args:
        ticker: Тикер инструмента (например, "SBER", "GAZP")
        timeframe: Таймфрейм ("1min", "15min", "1hour", "1day")
        num_candles: Количество свечей для отображения (по умолчанию 40)
    
    Returns:
        Tuple[BytesIO, str] буфер с изображением и реальный тикер или (None, None) при ошибке
    """
    actual_ticker = ticker  # Инициализируем переменную
    try:
        # Импортируем необходимые модули
        import matplotlib.pyplot as plt
        from matplotlib.ticker import ScalarFormatter
        import pytz
        import numpy as np
        import pandas as pd
        from tinkoff.invest import CandleInterval
        
        # Маппинг таймфреймов
        timeframe_mapping = {
            "1min": CandleInterval.CANDLE_INTERVAL_1_MIN,
            "15min": CandleInterval.CANDLE_INTERVAL_15_MIN,
            "1hour": CandleInterval.CANDLE_INTERVAL_HOUR,
            "1day": CandleInterval.CANDLE_INTERVAL_DAY
        }
        
        if timeframe not in timeframe_mapping:
            logger.error(f"Неподдерживаемый таймфрейм: {timeframe}")
            return None, None
        
        # Получаем исторические данные через Tinkoff API
        logger.info(f"Получение данных для {ticker} ({timeframe})...")
        
        # Используем существующий клиент Tinkoff
        tinkoff_client = get_tinkoff_client()
        if not tinkoff_client:
            logger.error("Не удалось получить клиент Tinkoff")
            return None, None
        
        # Получаем FIGI для тикера/названия компании
        try:
            with tinkoff_client.get_client() as client:
                # Сначала проверяем в локальном справочнике популярных акций
                ticker_upper = ticker.upper()
                if ticker_upper in EXTENDED_POPULAR_STOCKS:
                    figi = EXTENDED_POPULAR_STOCKS[ticker_upper]["figi"]
                    actual_ticker = ticker_upper
                    logger.info(f"Найден в локальном справочнике: {ticker_upper} (FIGI: {figi})")
                else:
                    # Ищем через API - сначала только акции
                    from tinkoff.invest.schemas import InstrumentType
                    
                    # Поиск акций по тикеру
                    shares_response = client.instruments.shares()
                    share_instrument = None
                    
                    # Ищем акцию по тикеру
                    for share in shares_response.instruments:
                        if share.ticker.upper() == ticker_upper:
                            share_instrument = share
                            break
                    
                    # Если не найдена по точному совпадению, ищем по частичному совпадению
                    if not share_instrument:
                        for share in shares_response.instruments:
                            if ticker_upper in share.ticker.upper() or share.ticker.upper() in ticker_upper:
                                # Проверяем, что это обычная акция (короткий тикер)
                                if (len(share.ticker) <= 6 and 
                                    share.ticker.isalpha() and 
                                    share.ticker.isupper()):
                                    share_instrument = share
                                    break
                    
                    # Если акция не найдена, пробуем общий поиск
                    if not share_instrument:
                        instruments = client.instruments.find_instrument(query=ticker)
                        if instruments.instruments:
                            # Ищем только акции среди найденных - берем первую найденную
                            for instrument in instruments.instruments:
                                if instrument.instrument_type == InstrumentType.INSTRUMENT_TYPE_SHARE:
                                    share_instrument = instrument
                                    break
                    
                    # Если все еще не найдена, берем первую акцию из общего списка
                    if not share_instrument and shares_response.instruments:
                        share_instrument = shares_response.instruments[0]
                    
                    if not share_instrument:
                        logger.error(f"Акция {ticker} не найдена")
                        return None, None
                    
                    figi = share_instrument.figi
                    actual_ticker = share_instrument.ticker
                    
                    logger.info(f"Найден инструмент: {share_instrument.name} (Тикер: {actual_ticker}, FIGI: {figi})")
            
        except Exception as e:
            logger.error(f"Ошибка поиска инструмента {ticker}: {e}")
            return None, None
        
        # Получаем исторические свечи
        try:
            from datetime import timedelta
            from tinkoff.invest.utils import now
            
            # Определяем период для запроса
            interval_durations = {
                CandleInterval.CANDLE_INTERVAL_1_MIN: timedelta(minutes=1),
                CandleInterval.CANDLE_INTERVAL_15_MIN: timedelta(minutes=15),
                CandleInterval.CANDLE_INTERVAL_HOUR: timedelta(hours=1),
                CandleInterval.CANDLE_INTERVAL_DAY: timedelta(days=1)
            }
            
            max_request_duration = {
                CandleInterval.CANDLE_INTERVAL_1_MIN: timedelta(hours=1),
                CandleInterval.CANDLE_INTERVAL_15_MIN: timedelta(days=1),
                CandleInterval.CANDLE_INTERVAL_HOUR: timedelta(days=7),
                CandleInterval.CANDLE_INTERVAL_DAY: timedelta(days=365)  # Увеличиваем лимит для дневных свечей
            }
            
            candle_duration = interval_durations[timeframe_mapping[timeframe]]
            total_needed = candle_duration * num_candles
            end_time = now()
            start_time = end_time - total_needed * 2  # Берем с запасом
            
            all_candles = []
            current_end = end_time
            
            with tinkoff_client.get_client() as client:
                while len(all_candles) < num_candles * 2:  # Собираем больше данных, чтобы точно хватило
                    current_start = max(start_time, current_end - max_request_duration[timeframe_mapping[timeframe]])
                    
                    candles = client.market_data.get_candles(
                        instrument_id=figi,
                        from_=current_start,
                        to=current_end,
                        interval=timeframe_mapping[timeframe]
                    ).candles
                    
                    if not candles:
                        break
                        
                    all_candles = candles[::-1] + all_candles  # Добавляем старые данные в начало
                    current_end = current_start
                    
                    if current_end < start_time:
                        break
                
                # Сортируем все свечи по времени и берем последние num_candles
                all_candles.sort(key=lambda x: x.time)
                all_candles = all_candles[-num_candles:]  # Берем самые последние свечи
            
            if not all_candles:
                logger.error(f"Нет данных для тикера {ticker}")
                return None, None
                
            # Форматирование в DataFrame
            data = [{
                'datetime': c.time,
                'open': c.open.units + c.open.nano/1e9,
                'high': c.high.units + c.high.nano/1e9,
                'low': c.low.units + c.low.nano/1e9,
                'close': c.close.units + c.close.nano/1e9,
                'volume': c.volume,
                'complete': c.is_complete,
                'ticker': actual_ticker
            } for c in all_candles[-num_candles:]]  # Берем последние N свечей (самые свежие)
            
            df = pd.DataFrame(data)
            
            # Фильтруем только завершенные свечи
            if 'complete' in df.columns:
                df = df[df['complete']].drop('complete', axis=1)
            
            if df.empty:
                logger.error(f"Нет завершенных данных для {ticker}")
                return None, None
                
            # Обрабатываем время
            df['datetime'] = pd.to_datetime(df['datetime'], utc=True)
            df['datetime'] = df['datetime'].dt.tz_convert('Europe/Moscow')
            df.set_index('datetime', inplace=True)
            
            # Сортируем по времени (от старых к новым)
            df = df.sort_index()
            
        except Exception as e:
            logger.error(f"Ошибка получения данных для {ticker}: {e}")
            return None, None
        
        # Настройка темной темы для графиков
        plt.style.use('dark_background')
        dark_blue = '#0a0e27'
        light_text = '#ffffff'
        light_grid = '#2a2a2a'
        
        plt.rcParams.update({
            'figure.facecolor': dark_blue,
            'axes.facecolor': dark_blue,
            'axes.edgecolor': light_text,
            'axes.labelcolor': light_text,
            'axes.titlecolor': light_text,
            'xtick.color': light_text,
            'ytick.color': light_text,
            'text.color': light_text,
            'grid.color': light_grid,
            'grid.alpha': 0.3,
            'legend.facecolor': dark_blue,
            'legend.edgecolor': light_text,
            'legend.labelcolor': light_text,
            'savefig.facecolor': dark_blue,
            'savefig.edgecolor': dark_blue
        })
        
        # Применяем темную тему
        try:
            plt.switch_backend('Agg')
        except Exception as e:
            logger.error(f"Ошибка настройки matplotlib: {e}")
            return None, None
        
        # Берем последние n свечей
        df_last = df.iloc[-num_candles:].copy()
        
        # Логируем порядок данных для отладки
        logger.info(f"🔧 CHART_DATA: Первая дата: {df_last.index[0]}, Последняя дата: {df_last.index[-1]}")
        logger.info(f"🔧 CHART_DATA: Количество свечей: {len(df_last)}")
        
        # Создаем график - свечи + объемы в двух подграфиках (Full HD)
        try:
            fig, (ax1, ax2) = plt.subplots(
                2, 1, 
                figsize=(19.2, 10.8),  # Full HD: 1920x1080 пикселей при 100 DPI
                gridspec_kw={'height_ratios': [3, 1]},
                sharex=True,
                dpi=100  # Стандартный DPI для Full HD
            )
        except Exception as e:
            logger.error(f"Ошибка создания графика matplotlib: {e}")
            return None, None
        
        # Преобразуем индексы во временные числа
        df_last['x'] = range(len(df_last))

        # --- Верхний график (Свечи) ---
        for idx, row in df_last.iterrows():
            color = '#00ffff' if row['close'] >= row['open'] else '#ff00ff'  # Бирюзовый для роста, пурпурный для падения
            body_height = abs(row['close'] - row['open'])
            
            # Фитиль
            ax1.vlines(
                x=row['x'], ymin=row['low'], ymax=row['high'], 
                color=color, linewidth=1.2, alpha=0.8
            )
            
            # Тело свечи
            ax1.bar(
                x=row['x'], height=body_height, 
                bottom=min(row['open'], row['close']),
                width=0.6, color=color, edgecolor=color, 
                linewidth=0.5, align='center'
            )

        # Настройки верхнего графика (свечи) - Full HD
        # Получаем название компании из справочника
        company_name = "Неизвестная компания"
        try:
            with tinkoff_client.get_client() as client:
                shares_response = client.instruments.shares()
                for share in shares_response.instruments:
                    if share.ticker == actual_ticker:
                        company_name = share.name
                        break
        except Exception as e:
            logger.warning(f"Не удалось получить название компании для {actual_ticker}: {e}")
        
        # Формируем заголовок с названием компании, тикером и временем генерации
        from datetime import datetime
        current_time = datetime.now().strftime("%d.%m.%Y %H:%M")
        
        # Добавляем информацию о периоде данных
        first_date = df_last.index[0].strftime("%d.%m.%Y")
        last_date = df_last.index[-1].strftime("%d.%m.%Y")
        period_info = f"Период: {first_date} - {last_date}"
        
        title = f'{company_name} ({actual_ticker}) - {timeframe} | {period_info} | Сгенерировано: {current_time}'
        
        ax1.set_title(title, fontsize=18, color='#ffffff', fontweight='bold', pad=20)
        ax1.grid(True, alpha=0.2, color='#2a2a2a')
        ax1.yaxis.tick_right()
        ax1.set_ylabel('Цена', color='#ffffff', fontsize=18)
        ax1.yaxis.set_major_formatter(ScalarFormatter(useMathText=True))
        ax1.ticklabel_format(style='plain', axis='y')

        # --- Нижний график (Объемы) ---
        colors = []
        for _, row in df_last.iterrows():
            colors.append('#00ffff' if row['close'] >= row['open'] else '#ff00ff')  # Бирюзовый для роста, пурпурный для падения
        
        ax2.bar(df_last['x'], df_last['volume'], color=colors, width=0.6, alpha=0.7)
        ax2.set_ylabel('Объем', color='#ffffff', fontsize=18)
        ax2.grid(True, alpha=0.2, color='#2a2a2a')
        ax2.yaxis.tick_right()
        ax2.yaxis.set_major_formatter(ScalarFormatter(useMathText=True))
        ax2.ticklabel_format(style='plain', axis='y')

        # Настройки нижнего графика (объемы) - Full HD
        ax2.set_title('Объем торгов', fontsize=18, color='#ffffff')

        # Форматирование времени в МСК формате
        moscow_tz = pytz.timezone('Europe/Moscow')
        
        # Конвертируем время в МСК и форматируем
        time_labels = []
        for idx in df_last.index:
            if idx.tzinfo is None:
                # Если время без часового пояса, считаем что это UTC
                moscow_time = pytz.UTC.localize(idx).astimezone(moscow_tz)
            else:
                moscow_time = idx.astimezone(moscow_tz)
            
            # Проверяем timeframe для выбора формата времени
            if timeframe == "1day":
                # Для дневных графиков используем формат "ММ.ДД"
                time_labels.append(moscow_time.strftime("%m.%d"))
            else:
                # Для остальных графиков используем формат "ЧЧ:ММ"
                time_labels.append(moscow_time.strftime("%H:%M"))
        
        # Устанавливаем метки времени каждые 5 свечей
        # Берем позиции каждые 5 свечей, начиная с первой
        tick_positions = df_last['x'].values[::5]
        tick_labels = [time_labels[i] for i in tick_positions]
        
        try:
            plt.xticks(tick_positions, tick_labels)
            
            # Настройка осей для обоих графиков - Full HD
            for ax in [ax1, ax2]:
                ax.tick_params(axis='both', which='both', length=0, colors='#ffffff', labelsize=14)
                for spine in ['top', 'right', 'left', 'bottom']:
                    ax.spines[spine].set_visible(False)
            
            plt.tight_layout()

            # Сохраняем в буфер - Full HD
            buf = BytesIO()
            plt.savefig(buf, format='png', dpi=100, bbox_inches='tight', facecolor='#0a0e27')
            logger.info(f"График создан в буфере (Full HD: 1920x1080)")
            plt.close()
            return buf, actual_ticker
            
        except Exception as e:
            logger.error(f"Ошибка сохранения графика matplotlib: {e}")
            return None, None
            
    except Exception as e:
        logger.error(f"Общая ошибка создания графика для {ticker}: {e}")
        return None, None

@tool
async def create_ticker_chart(
    ticker: Annotated[str, "Тикер инструмента (например, SBER, GAZP, YNDX)"],
    timeframe: Annotated[str, "Таймфрейм графика: 1min, 15min, 1hour, 1day (по умолчанию 1day)"] = "1day",
    num_candles: Annotated[int, "Количество свечей для отображения (по умолчанию 40)"] = 40,
    state: InjectedState = None
) -> Dict[str, Any]:
    """
    Создает график свечей по тикеру с объемами.
    
    Args:
        ticker: Тикер инструмента
        timeframe: Таймфрейм (1min, 15min, 1hour, 1day)
        num_candles: Количество свечей для отображения
    
    Returns:
        Словарь с результатом создания графика
    """
    try:
        logger.info(f"Создание графика для {ticker} ({timeframe}, {num_candles} свечей)")
        
        # Создаем график
        chart_buffer, actual_ticker = await plot_ticker_chart(ticker, timeframe, num_candles)
        
        if chart_buffer is None:
            return {
                "success": False,
                "error": f"Не удалось создать график для тикера {ticker}",
                "ticker": ticker,
                "timeframe": timeframe
            }
        
        # Конвертируем в base64 для передачи
        chart_buffer.seek(0)
        chart_base64 = base64.b64encode(chart_buffer.getvalue()).decode('utf-8')
        
        # Автоматически сохраняем PNG файл
        import os
        from datetime import datetime
        
        # Создаем имя файла с временной меткой
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        filename = f"{actual_ticker.lower()}_chart_{timeframe}_{timestamp}.png"
        
        # Сохраняем файл
        try:
            with open(filename, 'wb') as f:
                f.write(chart_buffer.getvalue())
            
            file_saved = True
            file_path = os.path.abspath(filename)
            file_size = os.path.getsize(filename)
            
            logger.info(f"График сохранен как: {filename} ({file_size} байт)")
            
        except Exception as e:
            logger.error(f"Ошибка сохранения файла {filename}: {e}")
            file_saved = False
            file_path = None
            file_size = 0
        
        # Создаем attachment для графика
        import uuid
        file_id = str(uuid.uuid4())
        
        result = {
            "success": True,
            "ticker": ticker,
            "actual_ticker": actual_ticker,
            "timeframe": timeframe,
            "num_candles": num_candles,
            "chart_base64": chart_base64,
            "file_saved": file_saved,
            "filename": filename if file_saved else None,
            "file_path": file_path,
            "file_size": file_size,
            "message": f"График для {actual_ticker} ({timeframe}) успешно создан и сохранен как {filename}" if file_saved else f"График для {actual_ticker} ({timeframe}) создан, но не сохранен",
            # Добавляем attachment для отображения
            "giga_attachments": [{
                "type": "image/png",
                "file_id": file_id,
                "data": chart_base64
            }]
        }
        
        logger.info(f"🔧 CREATE_TICKER_CHART: success={result['success']}, has_chart_base64={'chart_base64' in result}, chart_base64_length={len(result.get('chart_base64', ''))}, has_giga_attachments={'giga_attachments' in result}")
        return result
        
    except Exception as e:
        logger.error(f"Ошибка создания графика для {ticker}: {e}")
        return {
            "success": False,
            "error": f"Ошибка создания графика: {str(e)}",
            "ticker": ticker,
            "timeframe": timeframe
        }

@tool
def get_available_timeframes(
    state: InjectedState = None
) -> Dict[str, Any]:
    """
    Возвращает список доступных таймфреймов для графиков.
    
    Returns:
        Словарь с доступными таймфреймами
    """
    timeframes = {
        "1min": "1 минута",
        "15min": "15 минут", 
        "1hour": "1 час",
        "1day": "1 день"
    }
    
    return {
        "success": True,
        "timeframes": timeframes,
        "message": "Доступные таймфреймы для графиков"
    }

@tool
def get_popular_tickers(
    state: InjectedState = None
) -> Dict[str, Any]:
    """
    Возвращает список популярных российских акций.
    
    Returns:
        Словарь с популярными тикерами
    """
    return {
        "success": True,
        "tickers": EXTENDED_POPULAR_STOCKS,
        "message": f"Доступно {len(EXTENDED_POPULAR_STOCKS)} популярных российских акций"
    }

@tool
async def search_ticker_info(
    ticker: Annotated[str, "Тикер для поиска (например, SBER, GAZP)"],
    state: InjectedState = None
) -> Dict[str, Any]:
    """
    Поиск информации об инструменте по тикеру.
    
    Args:
        ticker: Тикер инструмента
    
    Returns:
        Словарь с информацией об инструменте
    """
    try:
        logger.info(f"Поиск информации для тикера {ticker}")
        
        # Сначала проверяем в локальном справочнике
        ticker_upper = ticker.upper()
        if ticker_upper in EXTENDED_POPULAR_STOCKS:
            stock_info = EXTENDED_POPULAR_STOCKS[ticker_upper]
            return {
                "success": True,
                "ticker": ticker_upper,
                "name": stock_info["name"],
                "figi": stock_info["figi"],
                "source": "local_database",
                "message": f"Найден в локальной базе: {stock_info['name']}"
            }
        
        # Если не найден локально, ищем через API
        tinkoff_client = get_tinkoff_client()
        if not tinkoff_client:
            return {
                "success": False,
                "error": "Не удалось получить клиент Tinkoff",
                "ticker": ticker
            }
        
        with tinkoff_client.get_client() as client:
            # Ищем только акции
            from tinkoff.invest.schemas import InstrumentType
            
            # Поиск акций по тикеру
            shares_response = client.instruments.shares()
            share_instrument = None
            
            # Ищем акцию по тикеру
            for share in shares_response.instruments:
                if share.ticker.upper() == ticker_upper:
                    share_instrument = share
                    break
            
            # Если не найдена по точному совпадению, ищем по частичному совпадению
            if not share_instrument:
                for share in shares_response.instruments:
                    if ticker_upper in share.ticker.upper() or share.ticker.upper() in ticker_upper:
                        # Проверяем, что это обычная акция (короткий тикер)
                        if (len(share.ticker) <= 6 and 
                            share.ticker.isalpha() and 
                            share.ticker.isupper()):
                            share_instrument = share
                            break
            
            # Если акция не найдена, пробуем общий поиск
            if not share_instrument:
                instruments = client.instruments.find_instrument(query=ticker)
                if instruments.instruments:
                    # Ищем только акции среди найденных - берем первую найденную
                    for instrument in instruments.instruments:
                        if instrument.instrument_type == InstrumentType.INSTRUMENT_TYPE_SHARE:
                            share_instrument = instrument
                            break
            
            # Если все еще не найдена, берем первую акцию из общего списка
            if not share_instrument and shares_response.instruments:
                share_instrument = shares_response.instruments[0]
            
            if not share_instrument:
                return {
                    "success": False,
                    "error": f"Акция {ticker} не найдена",
                    "ticker": ticker
                }
            
            return {
                "success": True,
                "ticker": share_instrument.ticker,
                "name": share_instrument.name,
                "figi": share_instrument.figi,
                "source": "tinkoff_api",
                "message": f"Найден через API: {share_instrument.name}"
            }
            
    except Exception as e:
        logger.error(f"Ошибка поиска тикера {ticker}: {e}")
        return {
            "success": False,
            "error": f"Ошибка поиска: {str(e)}",
            "ticker": ticker
        }

@tool
async def create_multiple_charts(
    tickers: Annotated[List[str], "Список тикеров для создания графиков"],
    timeframe: Annotated[str, "Таймфрейм графика: 1min, 15min, 1hour, 1day"] = "1day",
    num_candles: Annotated[int, "Количество свечей для отображения"] = 40,
    state: InjectedState = None
) -> Dict[str, Any]:
    """
    Создает графики для нескольких тикеров одновременно.
    
    Args:
        tickers: Список тикеров
        timeframe: Таймфрейм
        num_candles: Количество свечей
    
    Returns:
        Словарь с результатами создания графиков
    """
    try:
        logger.info(f"Создание графиков для {len(tickers)} тикеров: {tickers}")
        
        results = []
        successful = 0
        failed = 0
        
        for ticker in tickers:
            try:
                result = await create_ticker_chart.ainvoke({
                    "ticker": ticker, 
                    "timeframe": timeframe, 
                    "num_candles": num_candles
                })
                if result.get("success"):
                    successful += 1
                    results.append({
                        "ticker": ticker,
                        "success": True,
                        "actual_ticker": result.get("actual_ticker"),
                        "message": result.get("message")
                    })
                else:
                    failed += 1
                    results.append({
                        "ticker": ticker,
                        "success": False,
                        "error": result.get("error")
                    })
            except Exception as e:
                failed += 1
                results.append({
                    "ticker": ticker,
                    "success": False,
                    "error": f"Ошибка создания графика: {str(e)}"
                })
        
        return {
            "success": True,
            "total_tickers": len(tickers),
            "successful": successful,
            "failed": failed,
            "results": results,
            "message": f"Создано {successful} из {len(tickers)} графиков"
        }
        
    except Exception as e:
        logger.error(f"Ошибка создания множественных графиков: {e}")
        return {
            "success": False,
            "error": f"Ошибка создания графиков: {str(e)}",
            "tickers": tickers
        }

@tool
async def get_current_price(
    ticker: Annotated[str, "Тикер инструмента"],
    state: InjectedState = None
) -> Dict[str, Any]:
    """
    Получает текущую цену инструмента.
    
    Args:
        ticker: Тикер инструмента
    
    Returns:
        Словарь с текущей ценой
    """
    try:
        logger.info(f"Получение текущей цены для {ticker}")
        
        tinkoff_client = get_tinkoff_client()
        if not tinkoff_client:
            return {
                "success": False,
                "error": "Не удалось получить клиент Tinkoff",
                "ticker": ticker
            }
        
        # Получаем FIGI для тикера
        figi = None
        ticker_upper = ticker.upper()
        
        # Сначала проверяем в локальном справочнике
        if ticker_upper in EXTENDED_POPULAR_STOCKS:
            figi = EXTENDED_POPULAR_STOCKS[ticker_upper]["figi"]
        else:
            # Ищем через API - только акции
            with tinkoff_client.get_client() as client:
                from tinkoff.invest.schemas import InstrumentType
                
                # Поиск акций по тикеру
                shares_response = client.instruments.shares()
                share_instrument = None
                
                # Ищем акцию по тикеру
                for share in shares_response.instruments:
                    if share.ticker.upper() == ticker_upper:
                        share_instrument = share
                        break
                
                # Если не найдена по точному совпадению, ищем по частичному совпадению
                if not share_instrument:
                    for share in shares_response.instruments:
                        if ticker_upper in share.ticker.upper() or share.ticker.upper() in ticker_upper:
                            # Проверяем, что это обычная акция (короткий тикер)
                            if (len(share.ticker) <= 6 and 
                                share.ticker.isalpha() and 
                                share.ticker.isupper()):
                                share_instrument = share
                                break
                
                # Если акция не найдена, пробуем общий поиск
                if not share_instrument:
                    instruments = client.instruments.find_instrument(query=ticker)
                    if instruments.instruments:
                        # Ищем только акции среди найденных - берем первую найденную
                        for instrument in instruments.instruments:
                            if instrument.instrument_type == InstrumentType.INSTRUMENT_TYPE_SHARE:
                                share_instrument = instrument
                                break
                
                # Если все еще не найдена, берем первую акцию из общего списка
                if not share_instrument and shares_response.instruments:
                    share_instrument = shares_response.instruments[0]
                
                if share_instrument:
                    figi = share_instrument.figi
        
        if not figi:
            return {
                "success": False,
                "error": f"Не удалось найти FIGI для тикера {ticker}",
                "ticker": ticker
            }
        
        # Получаем текущую цену
        with tinkoff_client.get_client() as client:
            last_prices = client.market_data.get_last_prices(figi=[figi])
            if last_prices.last_prices:
                price_info = last_prices.last_prices[0]
                price = price_info.price.units + price_info.price.nano / 1e9
                
                return {
                    "success": True,
                    "ticker": ticker,
                    "figi": figi,
                    "price": price,
                    "currency": "RUB",  # Предполагаем рубли для российских акций
                    "time": price_info.time.isoformat(),
                    "message": f"Текущая цена {ticker}: {price:.2f} RUB"
                }
            else:
                return {
                    "success": False,
                    "error": f"Нет данных о цене для {ticker}",
                    "ticker": ticker
                }
                
    except Exception as e:
        logger.error(f"Ошибка получения цены для {ticker}: {e}")
        return {
            "success": False,
            "error": f"Ошибка получения цены: {str(e)}",
            "ticker": ticker
        }
