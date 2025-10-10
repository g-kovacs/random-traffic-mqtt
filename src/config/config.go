package config

import (
	"encoding/json"
	"github.com/g-kovacs/random-traffic-mqtt/internal/pointer"
	"log/slog"
)

func UnmarshalConfig(data []byte) (Config, error) {
	var r Config
	err := json.Unmarshal(data, &r)
	return r, err
}

func (r *Config) Marshal() ([]byte, error) {
	return json.Marshal(r)
}

func (c Config) LogValue() slog.Value {
	// Redact sensitive info if necessary
	redacted := c

	// Return structured slog.Value (a group)
	return slog.GroupValue(
		slog.Group("server",
			slog.String("host", redacted.Server.Host),
			slog.Int("port", redacted.Server.Port),
		),
		slog.Group("generation",
			slog.Int("frequency", redacted.Generation.Frequency),
			slog.Group("size",
				slog.String("distribution", string(redacted.Generation.Size.Distribution)),
				slog.Float64("parA", redacted.Generation.Size.ParA),
				slog.Float64("parB", pointer.SafeFloat64Ptr(redacted.Generation.Size.ParB)),
			),
		),
	)
}

type Config struct {
	// Message generation parameters
	Generation *Generation `json:"generation,omitempty" yaml:"generation,omitempty"`
	Loglevel   *Loglevel   `json:"loglevel,omitempty" yaml:"loglevel,omitempty"`
	// Server configuration
	Server *Server `json:"server,omitempty" yaml:"server,omitempty"`
}

// Message generation parameters
type Generation struct {
	// Message generation frequency in Hz
	Frequency int `json:"frequency,omitempty" yaml:"frequency,omitempty"`
	// Distribution of the generated message size
	Size Size `json:"size,omitempty" yaml:"size,omitempty"`
}

// Distribution of the generated message size
type Size struct {
	Distribution Distribution `json:"distribution,omitempty" yaml:"distribution,omitempty"`
	// First parameter of the chosen distribution
	ParA float64 `json:"parA,omitempty" yaml:"parA,omitempty"`
	// Second parameter of the chosen distribution
	ParB *float64 `json:"parB,omitempty" yaml:"parB,omitempty"`
}

// Server configuration
type Server struct {
	// Hostname or IP address of the remote server
	Host string `json:"host" yaml:"host"`
	// Port to connect to
	Port int `json:"port" yaml:"port"`
}

// Some common distributions
type Distribution string

const (
	Exponential Distribution = "exponential"
	Normal      Distribution = "normal"
)

// Log level
type Loglevel string

const (
	Debug Loglevel = "Debug"
	Error Loglevel = "Error"
	Info  Loglevel = "Info"
	Warn  Loglevel = "Warn"
)
