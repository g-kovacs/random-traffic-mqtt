package client

import (
	"context"
	"crypto/rand"
	"fmt"
	"log/slog"
	"net/url"
	"os"
	"os/signal"
	"syscall"
	"time"

	"github.com/eclipse/paho.golang/autopaho"
	"github.com/eclipse/paho.golang/paho"
	"github.com/g-kovacs/random-traffic-mqtt/internal/distribution"
	"github.com/g-kovacs/random-traffic-mqtt/src/config"
	"github.com/google/uuid"
)

type Client struct {
	Random distribution.Distribution
}

func (c Client) mqttConfig(cfg config.Config) autopaho.ClientConfig {
	urlString := fmt.Sprintf("mqtt://%s:%d", cfg.Server.Host, cfg.Server.Port)
	u, err := url.Parse(urlString)
	if err != nil {
		slog.Error("error parsing url", "error", err.Error())
		os.Exit(-1)
	}

	cliCfg := autopaho.ClientConfig{
		ServerUrls:                    []*url.URL{u},
		ConnectUsername:               cfg.Server.User,
		ConnectPassword:               []byte(cfg.Server.Pass),
		KeepAlive:                     20,
		CleanStartOnInitialConnection: true,
		SessionExpiryInterval:         60,
		OnConnectError:                func(err error) { slog.Error("cannot connect to server", "reason", err.Error()) },
		ClientConfig: paho.ClientConfig{
			ClientID: uuid.NewString(),
			OnServerDisconnect: func(d *paho.Disconnect) {
				if d.Properties != nil {
					slog.Error("server disconnect", "reasonString", d.Properties.ReasonString)
				} else {
					slog.Error("server disconnect", "reasonCode", d.ReasonCode)
				}
			},
		},
	}
	return cliCfg
}

func (c Client) newMessage() ([]byte, error) {
	size := c.Random.Next()
	b := make([]byte, size)
	_, err := rand.Read(b)
	if err != nil {
		return nil, err
	}
	return b, nil
}

func (c Client) Run(cfg config.Config) {
	ctx, stop := signal.NotifyContext(context.Background(), os.Interrupt, syscall.SIGTERM)
	defer stop()

	pahoConfig := c.mqttConfig(cfg)

	conn, err := autopaho.NewConnection(ctx, pahoConfig)
	if err != nil {
		panic(err)
	}

	if err = conn.AwaitConnection(ctx); err != nil {
		panic(err)
	}

	ticker := time.NewTicker(time.Duration(1000/cfg.Generation.Frequency) * time.Millisecond)
	defer ticker.Stop()

	for {
		select {
		case <-ticker.C:
			p, err := c.newMessage()
			if err != nil {
				slog.Error("error generating message", "reason", err.Error())
			}
			if _, err = conn.Publish(ctx, &paho.Publish{
				QoS:     0,
				Topic:   cfg.Server.Topic,
				Payload: p,
			}); err != nil {
				if ctx.Err() == nil {
					panic(err)
				}
			}
			slog.Debug("sent message", "size", len(p), "message", p)
			continue
		case <-ctx.Done():
		}
		break
	}
	slog.Info("exiting")
	<-conn.Done()

}
