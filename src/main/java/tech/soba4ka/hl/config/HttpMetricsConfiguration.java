package tech.soba4ka.hl.config;

import io.micrometer.observation.ObservationPredicate;
import org.springframework.context.annotation.Bean;
import org.springframework.context.annotation.Configuration;
import org.springframework.http.server.observation.ServerRequestObservationContext;

@Configuration(proxyBeanMethods = false)
public class HttpMetricsConfiguration {
    @Bean
    ObservationPredicate excludeServiceEndpoints() {
        return (name, context) -> {
            if (context instanceof ServerRequestObservationContext serverContext) {
                var request = serverContext.getCarrier();
                if (request != null) {
                    String path = request.getRequestURI().substring(request.getContextPath().length());
                    return !path.equals("/health") && !path.equals("/metrics") && !path.equals("/handlers");
                }
            }
            return true;
        };
    }
}
