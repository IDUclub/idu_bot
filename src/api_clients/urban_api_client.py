import geopandas as gpd
import pandas as pd

from src.common.api_handlers.json_api_handler import JSONAPIHandler
from src.common.exceptions.http_exception import http_exception

LIVING_BUILDINGS_ID = 4


class UrbanAPIClient:

    def __init__(self, json_handler: JSONAPIHandler) -> None:
        self.json_handler = json_handler
        self.__name__ = "UrbanAPIClient"

    async def get_buffers_for_scenario(
        self, scenario_id: int, token: str
    ) -> gpd.GeoDataFrame:
        """
        Function retrieves buffers for a scenario
        Args:
            scenario_id (int): scenario id to get data from
            token (str): access token to retrieve data from
        Returns:
            gpd.GeoDataFrame: gpd.GeoDataFrame with buffers to get data from
        """

        endpoint_url = f"/api/v1/scenarios/{scenario_id}/buffers"
        result = await self.json_handler.get(
            endpoint_url, headers={"Authorization": f"Bearer {token}"}
        )
        return gpd.GeoDataFrame.from_features(result)

    async def get_scenario_data(self, scenario_id: int, token: str) -> pd.DataFrame:
        """

        Args:
            scenario_id (int):
            token (scenario_id):

        Returns:

        """
