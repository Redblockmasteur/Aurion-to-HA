# Aurion Planning Integration for Home Assistant

This integration allows you to fetch and display your **Aurion planning** in Home Assistant using the [Mauria API](https://mauria-api.fly.dev).

## Features
- **UI Configuration**: Add the integration via the Home Assistant UI.
- **Mauria API**: Uses the Mauria API wrapper to fetch Aurion planning data.
- **Automatic Updates**: Regularly polls the API for new events.
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

## Sensor Attributes

The integration creates a sensor with the following attributes:

| Attribute | Description | Example |
|-----------|-------------|---------|
| `events` | List of planning events (JSON array) | `[{"id": "1", "title": "Cours de Maths", "start": "2024-06-10T08:00:00", "end": "2024-06-10T10:00:00", "allDay": false, "editable": false, "className": "cours"}]` |
| `last_updated` | Timestamp of the last update | `2024-06-10T12:00:00.000000+00:00` |

---

## Example Usage

### Automations

You can create automations based on planning events. For example, notify when a new event is added:

```yaml
automation:
  - alias: "Notify on new Aurion event"
    trigger:
      - platform: state
        entity_id: sensor.aurion_planning_your_email
    action:
      - service: notify.notify
        data:
          message: "New event in Aurion planning!"
```

### Templates

Extract event details using templates:

```yaml
sensor:
  - platform: template
    sensors:
      next_aurion_event:
        value_template: >
          {% if state_attr('sensor.aurion_planning_your_email', 'events') | length > 0 %}
            {{ state_attr('sensor.aurion_planning_your_email', 'events')[0].title }}
          {% else %}
            No events
          {% endif %}
        attribute_templates:
          start_time: >
            {% if state_attr('sensor.aurion_planning_your_email', 'events') | length > 0 %}
              {{ state_attr('sensor.aurion_planning_your_email', 'events')[0].start }}
            {% endif %}
```

### Calendar Integration (Advanced)

You can create a calendar entity using the [Home Assistant Calendar integration](https://www.home-assistant.io/integrations/calendar/) with a template:

```yaml
calendar:
  - platform: template
    name: "Aurion Planning"
    events:
      - name: "{{ event.title }}"
        start: "{{ event.start }}"
        end: "{{ event.end }}"
        data:
          events: >
            {{ state_attr('sensor.aurion_planning_your_email', 'events') }}
```

---

## API Reference

This integration uses the [Mauria API](https://mauria-api.fly.dev) with the following endpoints:

- **`POST /aurion/login`**: Authenticate with Aurion credentials.
- **`POST /aurion/planning`**: Fetch planning events for a given date range.

For more details, see the [Mauria API documentation](https://mauria-api.fly.dev/json).

---

## Troubleshooting

### Authentication Failed
- Verify your **email and password** are correct.
- Ensure your Aurion account is **active** and accessible.

### Connection Error
- Check your **internet connection**.
- Verify the Mauria API is **online** (https://mauria-api.fly.dev).

### No Events Showing
- Ensure your Aurion account has **planning events**.
- Check the **planning range** in the integration options (default: 60 days).

---

## Development

### Testing
1. Place the `custom_components/aurion_planning` folder in your Home Assistant `custom_components` directory.
2. Restart Home Assistant.
3. Add the integration via the UI.

### Logging
Enable debug logging for this integration:

```yaml
logger:
  default: info
  logs:
    custom_components.aurion_planning: debug
```

---

## License

This project is licensed under the **MIT License**. See [LICENSE](LICENSE) for details.

---

## Credits

- **Author**: [Redblockmasteur](https://github.com/Redblockmasteur)
- **API**: [Mauria API](https://github.com/MauriaApp/API-v2) by [MauriaApp](https://github.com/MauriaApp)
