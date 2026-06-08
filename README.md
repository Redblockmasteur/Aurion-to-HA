# Aurion Integration for Home Assistant

This integration allows you to fetch and display your **Aurion planning and absences** in Home Assistant using the [Mauria API](https://mauria-api.fly.dev).

## Features
- **UI Configuration**: Add the integration via the Home Assistant UI.
- **Mauria API**: Uses the Mauria API wrapper to fetch Aurion data.
- **Automatic Updates**: Regularly polls the API for new data.
- **Multiple Sensors**:
  - **Planning**: Fetch and display your Aurion planning events.
  - **Absences**: Display the total number of absences and detailed list.
- **Customizable Range**: Configure how many days of planning to fetch (default: 60 days).

---

## Installation

### Method 1: HACS (Recommended)
1. Add this repository as a custom repository in HACS.
2. Install the integration via HACS.
3. Restart Home Assistant.

### Method 2: Manual
1. Copy the `custom_components/aurion_planning` folder to your Home Assistant `custom_components` directory.
2. Restart Home Assistant.

---

## Configuration

1. **Add the Integration**:
   - Go to **Settings > Devices & Services** in Home Assistant.
   - Click **Add Integration** and search for **Aurion Planning (Mauria API)**.
   - Enter your **Aurion email and password** when prompted.

2. **Configure Options (Optional)**:
   - After setup, you can adjust:
     - **Update interval** (default: 30 minutes).
     - **Planning range** (default: 60 days).

---

## Sensors

The integration creates **two sensors** for each Aurion account:

### 1. Planning Sensor
- **Entity ID**: `sensor.aurion_planning_<your_email>`
- **State**: Timestamp of the last update.
- **Attributes**:
  | Attribute | Description | Example |
  |-----------|-------------|---------|
  | `events` | List of planning events (JSON array) | `[{"id": "1", "title": "Cours de Maths", "start": "2024-06-10T08:00:00", "end": "2024-06-10T10:00:00", "allDay": false, "editable": false, "className": "cours"}]` |
  | `last_updated` | Timestamp of the last update | `2024-06-10T12:00:00.000000+00:00` |

### 2. Absences Sensor
- **Entity ID**: `sensor.aurion_absences_<your_email>`
- **State**: **Total number of absences** (e.g., `12`).
- **Attributes**:
  | Attribute | Description | Example |
  |-----------|-------------|---------|
  | `absences` | List of absences (JSON array) | `[{"date": "12/03/26", "type": "Absence non excusée", "duration": "2:00", "time": "08:00 - 10:00", "class": "Communication et Supervision Industrielle", "teacher": "Moez BELHAOUANE"}]` |
  | `last_updated` | Timestamp of the last update | `2024-06-10T12:00:00.000000+00:00` |
  | `total_absences` | Total number of absences | `12` |

---

## Example Usage

### Automations

#### 1. Notify on New Absence
```yaml
automation:
  - alias: "Notify on new absence"
    trigger:
      - platform: state
        entity_id: sensor.aurion_absences_your_email
    condition:
      - condition: template
        value_template: >
          {{ trigger.to_state.state | int > trigger.from_state.state | int }}
    action:
      - service: notify.notify
        data:
          message: "Nouvelle absence détectée ! Total: {{ trigger.to_state.state }} absences."
```

#### 2. Notify on Planning Update
```yaml
automation:
  - alias: "Notify on planning update"
    trigger:
      - platform: state
        entity_id: sensor.aurion_planning_your_email
    action:
      - service: notify.notify
        data:
          message: "Votre planning Aurion a été mis à jour !"
```

### Templates

#### 1. Next Class
```yaml
sensor:
  - platform: template
    sensors:
      next_class:
        value_template: >
          {% if state_attr('sensor.aurion_planning_your_email', 'events') | length > 0 %}
            {{ state_attr('sensor.aurion_planning_your_email', 'events')[0].title }}
          {% else %}
            Aucun cours
          {% endif %}
        attribute_templates:
          start_time: >
            {% if state_attr('sensor.aurion_planning_your_email', 'events') | length > 0 %}
              {{ state_attr('sensor.aurion_planning_your_email', 'events')[0].start }}
            {% endif %}
```

#### 2. Last Absence Details
```yaml
sensor:
  - platform: template
    sensors:
      last_absence:
        value_template: >
          {% if state_attr('sensor.aurion_absences_your_email', 'absences') | length > 0 %}
            {{ state_attr('sensor.aurion_absences_your_email', 'absences')[0].date }} - 
            {{ state_attr('sensor.aurion_absences_your_email', 'absences')[0].class }}
          {% else %}
            Aucune absence
          {% endif %}
```

### Dashboards (Lovelace)

#### 1. Absences Card
```yaml
type: entities
entities:
  - entity: sensor.aurion_absences_your_email
    name: Total Absences
    secondary_info: last-updated
```

#### 2. Planning Card
```yaml
type: entities
entities:
  - entity: sensor.aurion_planning_your_email
    name: Planning
    secondary_info: last-updated
```

---

## API Reference

This integration uses the [Mauria API](https://mauria-api.fly.dev) with the following endpoints:

- **`POST /aurion/login`**: Authenticate with Aurion credentials.
- **`POST /aurion/planning`**: Fetch planning events for a given date range.
- **`POST /aurion/absences`**: Fetch absences data.

For more details, see the [Mauria API documentation](https://mauria-api.fly.dev/json).

---

## Troubleshooting

### Authentication Failed
- Verify your **email and password** are correct.
- Ensure your Aurion account is **active** and accessible.

### Connection Error
- Check your **internet connection**.
- Verify the Mauria API is **online** (https://mauria-api.fly.dev).

### No Data Showing
- Ensure your Aurion account has **planning events** or **absences**.
- Check the **planning range** in the integration options (default: 60 days).
- Enable debug logging (see below).

### Enable Debug Logging
Add the following to your `configuration.yaml`:
```yaml
logger:
  default: info
  logs:
    custom_components.aurion_planning: debug
```

---

## Development

### Testing
1. Place the `custom_components/aurion_planning` folder in your Home Assistant `custom_components` directory.
2. Restart Home Assistant.
3. Add the integration via the UI.

### Contributing
Feel free to open issues or pull requests on the [GitHub repository](https://github.com/Redblockmasteur/Aurion-to-HA).

---

## License

This project is licensed under the **MIT License**. See [LICENSE](LICENSE) for details.

---

## Credits

- **Author**: [Redblockmasteur](https://github.com/Redblockmasteur)
- **API**: [Mauria API](https://github.com/MauriaApp/API-v2) by [MauriaApp](https://github.com/MauriaApp)
