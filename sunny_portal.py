from requests_html import HTMLSession
import json
import pandas as pd
import io


class SunnyPortal:
    BASE_URL = 'https://www.sunnyportal.com'
    LOGIN_URL = '{}/Templates/Start.aspx'.format(BASE_URL)
    PLANTS_URL = '{}/Plants/GetPlantList'.format(BASE_URL)
    PLANTS_DASHBOARD_URL = '{}/RedirectToPlant'.format(BASE_URL)
    INVERTERS_URL = '{}/FixedPages/InverterSelection.aspx'.format(BASE_URL)
    DOWNLOAD_URL = '{}/Templates/DownloadDiagram.aspx?down=diag'.format(BASE_URL)

    class SessionDecorators:
        def __init__(self, func):
            self.func = func

        def __call__(self, *args):
            sess = args[0]
            if sess is None:
                raise Exception('Session needs to be initialized. Try calling the create_session method first')
            return self.func(self, *args)

    def __init__(self, username, password):
        self.username = username
        self.password = password
        self.session = None

    def create_session(self):
        self.session = HTMLSession()
        login = self.session.get(SunnyPortal.LOGIN_URL)
        login.html.render()
        view_state = list(set(login.html.xpath("//input[@name='__VIEWSTATE']/@value")))[0]
        view_state_generator = list(set(login.html.xpath("//input[@name='__VIEWSTATEGENERATOR']/@value")))[0]
        user_payload = {
            '__EVENTTARGET': '',
            '__EVENTARGUMENT': '',
            '__VIEWSTATE': view_state,
            '__VIEWSTATEGENERATOR': view_state_generator,
            'ctl00$ContentPlaceHolder1$Logincontrol1$LoginBtn': 'Login',
            'ctl00$ContentPlaceHolder1$Logincontrol1$txtUserName': self.username,
            'ctl00$ContentPlaceHolder1$Logincontrol1$txtPassword': self.password,
            'ctl00$ContentPlaceHolder1$Logincontrol1$ServiceAccess': True
        }
        self.session.post(SunnyPortal.LOGIN_URL, data=user_payload)

    @SessionDecorators
    def get_plants_info(self, session):
        self.session = session
        plant_list = self.session.get(SunnyPortal.PLANTS_URL)
        plant_list_json = json.loads(plant_list.content)
        rows = [{key: value for (key, value) in x.items()} for x in plant_list_json['aaData']]
        plant_info_df = pd.DataFrame(rows)
        return plant_info_df

    @SessionDecorators
    def get_plant_inverters_info(self, session, plant_id, plant_name, date):
        self.session = session
        plant_info = self.session.get(
            '{}/{}'.format(SunnyPortal.PLANTS_DASHBOARD_URL, plant_id)
        )
        check_inverter_exists = plant_info.html.xpath(
            "//*[@id='lmiInverterSelection']"
        )
        if len(check_inverter_exists) >= 1:
            select_inverters = self.session.get(SunnyPortal.INVERTERS_URL)
            diagram_viewstate = list(set(select_inverters.html.xpath(
                "//input[@name='__ctl00$ContentPlaceHolder1$UserControlShowInverterSelection1$_diagram_VIEWSTATE']/@value"
            )))[0]
            inv_payload = {
                "__EVENTTARGET": '',
                "__EVENTARGUMENT": '',
                "__LASTFOCUS": '',
                "__ctl00$ContentPlaceHolder1$UserControlShowInverterSelection1$_diagram_VIEWSTATE": diagram_viewstate,
                "ctl00$HiddenPlantOID": plant_id,
                "ctl00$ContentPlaceHolder1$UserControlShowInverterSelection1$DeviceSelection$SelectAllCheckBox": "on",
                "ctl00$ContentPlaceHolder1$UserControlShowInverterSelection1$DeviceSelection$HiddenPlantOID": plant_id,
                "ctl00$ContentPlaceHolder1$UserControlShowInverterSelection1$DeviceSelection$HasSelectAllCheckboxField": 1,
                "ctl00$ContentPlaceHolder1$UserControlShowInverterSelection1$SelectedIntervalID": 3,
                "ctl00$ContentPlaceHolder1$UserControlShowInverterSelection1$PlantName": plant_name,
                "ctl00$ContentPlaceHolder1$UserControlShowInverterSelection1$UseIntervalHour": 0,
                "ctl00$ContentPlaceHolder1$UserControlShowInverterSelection1$_datePicker$textBox": date
            }
            self.session.post(SunnyPortal.INVERTERS_URL, data=inv_payload)
            download_result = self.session.get(SunnyPortal.DOWNLOAD_URL)
            data = download_result.content.decode('utf8')
            # try:
            inverters_df = pd.read_csv(io.StringIO(data), sep=';')
            return inverters_df
            # except pd.io.common.EmptyDataError:
            #     print("File is empty")
        else:
            return "No inverter found for this plant"

    @SessionDecorators
    def get_plant_inverters_devices(self, session, plant_id):
        self.session = session
        plant_info = self.session.get(
            '{}/{}'.format(SunnyPortal.PLANTS_DASHBOARD_URL, plant_id)
        )
        check_inverter_exists = plant_info.html.xpath(
            "//*[@id='lmiInverterSelection']"
        )
        if len(check_inverter_exists) >= 1:
            select_inverters = self.session.get(SunnyPortal.INVERTERS_URL)
            device_table = select_inverters.html.xpath(
                "//table[@id='ctl00_ContentPlaceHolder1_UserControlShowInverterSelection1_DeviceSelection_SimpleCheckboxList']//tr"
            )
            device_string = [td.text for td in device_table][0]
            devices = device_string.split('\n')
            return devices
        else:
            return "No inverter found for site {}".format(plant_id)
