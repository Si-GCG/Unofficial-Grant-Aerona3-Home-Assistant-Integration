To use copy the wc-plotter file and place it in the www folder of your Home Assistant instance. then create a button on the dashboard of your choice and just click the button.
Enter your design temps and if you like the current OAT. Then use the sliders to adjust your test curve. I have found using the full range of your ashp works well then adjust it left and right using the OAT max and min values.

Huge shout out to DamonC for the original app that he built, that led to this UI
you can find his original here: https://heat-curve-plotter.lovable.app

## Blueprints

The `blueprints/` folder has Home Assistant automation blueprints for adjusting the flow temperature automatically:

- `adaptive_flow_temp.yaml`: fixed flow temperature control based on outdoor and indoor temperatures, re-evaluated every 15 minutes.
- `adaptive_weather_compensation_zone1.yaml` and `adaptive_weather_compensation_zone2.yaml`: adjust the flow temperature for Zone 1 or Zone 2 every 15 minutes from the forecast, wind chill, actual outdoor conditions and the average indoor temperature. If the matching Heating Weather Compensation switch is on, they adjust Max Flow (Tm1); otherwise they drive the Fixed Flow set point.

To use one, copy the file into `config/blueprints/automation/grant_aerona3/` on your Home Assistant instance, then go to Settings → Automations & Scenes → Blueprints and create an automation from it. You choose your own weather, temperature and Grant Aerona3 entities when you create the automation.
